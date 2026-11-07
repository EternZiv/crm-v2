"""
API mixins for implementing advanced features like search, filtering, bulk update, and bulk delete
"""

# Standard library imports
from functools import reduce
from operator import or_

# Third-party imports (other)
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response

# First party imports (Finlo)
from finlo.contrib.core.authorization import (
    get_company_scope,
    scope_queryset_to_company,
)
from finlo.contrib.core.sales_authorization import has_effective_permission
from finlo.contrib.core.utils import get_allowed_user_ids
from finlo.contrib.generics.views.helpers.queryset_utils import (
    get_granted_access_filter,
)
from finlo.db import transaction
from finlo.db.models import Q


def scope_queryset_to_permission(queryset, user, action: str, request=None):
    """
    Narrow ``queryset`` to the rows ``user`` is allowed to act on for
    ``action`` ("view", "change" or "delete"), mirroring the object-level
    rule in finlo.contrib.generics.views.details._check_record_permission:
    the global ``{action}_{model}`` permission grants every row in the
    caller's authorized company scope, the
    ``{action}_own_{model}`` permission grants only rows the user owns (via
    OWNER_FIELDS) or has been explicitly granted access to.

    Returns ``queryset.none()`` if the user has neither permission, so
    callers never fall back to an unrestricted queryset.
    """
    queryset = scope_queryset_to_company(queryset, user, request)
    if user.is_superuser:
        return queryset

    model = queryset.model
    app_label = model._meta.app_label
    model_name = model._meta.model_name

    has_global = has_effective_permission(
        user, f"{app_label}.{action}_{model_name}"
    )
    has_own = has_effective_permission(
        user, f"{app_label}.{action}_own_{model_name}"
    )

    if has_global:
        return queryset
    if not has_own:
        return queryset.none()

    owner_fields = getattr(model, "OWNER_FIELDS", None)
    ownership_query = None
    if owner_fields:
        allowed_user_ids = get_allowed_user_ids(user)
        ownership_query = reduce(
            or_,
            (Q(**{f"{field}__in": allowed_user_ids}) for field in owner_fields),
            Q(),
        )

    granted_query = get_granted_access_filter(model, user, action)
    if granted_query is not None:
        ownership_query = (
            granted_query
            if ownership_query is None
            else ownership_query | granted_query
        )

    if ownership_query is None:
        return queryset.none()
    return queryset.filter(ownership_query)
class CompanyScopedSerializerMixin:
    """
    Serializer mixin for FinloCoreModel subclasses that ignores any
    client-supplied ``company`` value and derives it server-side from the
    request instead, matching the classic (non-DRF) create-form flow in
    finlo.contrib.generics.views.single_form.FinloFormView.form_valid,
    which always assigns request.active_company (falling back to
    request.user.company) regardless of what the form posted.

    Non-superusers cannot submit a different company than their authorized
    scope. Django superusers retain explicit cross-company assignment access.
    """

    def validate(self, attrs):
        """Force ``company`` to the request's active company, ignoring any submitted value."""
        attrs = super().validate(attrs)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if (
            user is None
            or not user.is_authenticated
            or user.is_superuser
            or getattr(getattr(user, "role", None), "system_key", None)
            == "SUPER_ADMIN"
        ):
            return attrs

        scope = get_company_scope(user, request)
        if scope.company_id is None:
            raise serializers.ValidationError(
                {"company": "Your account is not assigned to a company."}
            )

        if "company" in attrs:
            submitted_company = attrs["company"]
            if (
                submitted_company is None
                or submitted_company.pk != scope.company_id
            ):
                raise serializers.ValidationError(
                    {"company": "You cannot assign records to another company."}
                )

        instance = getattr(self, "instance", None)
        if instance is not None and instance.company_id != scope.company_id:
            raise serializers.ValidationError(
                {"company": "You cannot modify records outside your active company."}
            )

        role_key = getattr(getattr(user, "role", None), "system_key", None)
        if role_key in {"HEAD_OF_SALES", "RSM", "SSM", "ASM", "BDO"}:
            model = instance.__class__ if instance is not None else self.Meta.model
            for field_name in getattr(model, "OWNER_FIELDS", ()):
                if field_name not in attrs and field_name not in self.initial_data:
                    continue
                submitted = attrs.get(field_name, self.initial_data.get(field_name))
                submitted_id = getattr(submitted, "pk", submitted)
                if isinstance(submitted_id, str) and submitted_id.isdecimal():
                    submitted_id = int(submitted_id)
                if instance is None:
                    if submitted_id is not None and submitted_id != user.pk:
                        raise serializers.ValidationError(
                            {
                                field_name: "Sales roles cannot assign records to another owner."
                            }
                        )
                    continue

                previous = getattr(instance, field_name, None)
                if getattr(previous, "pk", previous) != submitted_id:
                    raise serializers.ValidationError(
                        {
                            field_name: "Sales roles cannot transfer record ownership."
                        }
                    )

        company = self.fields["company"].queryset.filter(
            pk=scope.company_id
        ).first()
        if company is None:
            raise serializers.ValidationError(
                {"company": "Your active company could not be found."}
            )
        attrs["company"] = company
        return attrs


class SearchFilterMixin:
    """
    Mixin to add search and filtering capabilities to ViewSets
    """

    search_fields = []  # Fields to search in, should be overridden in the ViewSet
    filterset_fields = []  # Fields to filter by, should be overridden in the ViewSet

    # Actions that return a list of objects (rather than a single object
    # reached via get_object()) and must therefore be scoped, at queryset
    # level, to rows the user has view/view_own permission on. Opt-in via
    # this attribute (or the `list_actions` attribute for extra actions
    # beyond "list") rather than on-by-default, since not every ViewSet
    # using this mixin is protected by FinloModelPermissions' view/view_own
    # codenames -- e.g. ViewSets with a bespoke ownership model (a plain
    # `user` field checked by their own permission class) must scope their
    # own queryset instead and should leave this False.
    scope_list_to_view_permission = False

    def get_queryset(self):
        """
        Override get_queryset to add search and filtering capabilities,
        and, when opted in via scope_list_to_view_permission, to scope
        list-type actions down to rows the requesting user actually has
        view (or view_own) permission on. Detail actions (retrieve/update/
        destroy) are left to check_object_permissions, which applies the
        same OWNER_FIELDS rule per object.
        """
        queryset = super().get_queryset()

        action = getattr(self, "action", None)
        request = getattr(self, "request", None)
        if request is not None and request.user.is_authenticated:
            queryset = scope_queryset_to_company(queryset, request.user, request)
        if (
            self.scope_list_to_view_permission
            and request is not None
            and action in getattr(self, "list_actions", ("list",))
        ):
            queryset = scope_queryset_to_permission(
                queryset, request.user, "view", request=request
            )

        # Apply search if search parameter is provided
        search_term = self.request.query_params.get("search", None)
        if search_term and self.search_fields:
            q_objects = Q()
            for field in self.search_fields:
                q_objects |= Q(**{f"{field}__icontains": search_term})
            queryset = queryset.filter(q_objects)

        # Apply filtering for each filter parameter
        for param, value in self.request.query_params.items():
            if param in self.filterset_fields and value:
                queryset = queryset.filter(**{param: value})

        return queryset


class BulkOperationsMixin:
    """
    Mixin to add bulk update and bulk delete capabilities to ViewSets
    with support for filtering operations
    """

    def _sanitize_bulk_update_data(self, raw_data):
        """
        Reduce ``raw_data`` to the fields the ViewSet's serializer actually
        allows a client to write, running it through the same
        read_only_fields/write_only/validate() pipeline that a normal
        PATCH goes through.

        bulk_update operates on a queryset with .update(**data) instead of
        per-instance serializer.save(), so without this step it would
        completely bypass every serializer-level protection -- read_only
        fields (e.g. FinloUserSerializer.is_superuser/is_staff),
        write_only secrets, and CompanyScopedSerializerMixin's forcing of
        `company` from the request. Returns (validated_data, error_response);
        error_response is None on success.
        """
        model = self.get_queryset().model
        role_key = getattr(
            getattr(self.request.user, "role", None), "system_key", None
        )
        if role_key in {"HEAD_OF_SALES", "RSM", "SSM", "ASM", "BDO"}:
            attempted_owner_fields = set(raw_data) & set(
                getattr(model, "OWNER_FIELDS", ())
            )
            if attempted_owner_fields:
                return None, Response(
                    {
                        "error": "Sales roles cannot transfer record ownership.",
                        "fields": sorted(attempted_owner_fields),
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        serializer = self.get_serializer(data=raw_data, partial=True)
        if not serializer.is_valid():
            return None, Response(
                {
                    "error": "Invalid 'data' for bulk update",
                    "details": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        validated = dict(serializer.validated_data)
        # Only plain columns/FKs can be set via queryset.update(); M2M
        # fields (e.g. User.user_permissions/groups, Report.shared_with)
        # raise FieldError there and always required per-instance .set()
        # instead, so drop them rather than let bulk_update crash -- this
        # doesn't newly expose anything, since M2M bulk assignment via
        # .update() was never possible.
        concrete_field_names = {
            f.name for f in model._meta.get_fields() if not f.many_to_many
        }
        validated = {k: v for k, v in validated.items() if k in concrete_field_names}
        # write_only fields (e.g. password, mail credentials/tokens) still
        # appear in validated_data -- write_only only hides them from
        # output. A serializer's create()/update() override normally does
        # extra work for these (e.g. FinloUserSerializer hashes password
        # via set_password()); queryset.update() would instead write the
        # raw value straight into the column, so drop any field the
        # serializer declared write_only rather than silently corrupt it.
        write_only_fields = {
            name
            for name, field in serializer.fields.items()
            if getattr(field, "write_only", False)
        }
        validated = {k: v for k, v in validated.items() if k not in write_only_fields}
        return validated, None

    def _apply_filters_to_queryset(self, queryset, filters):
        """
        Apply filters to queryset based on provided filter criteria

        Filter format:
        {
            "field1": "value1",
            "field2__contains": "value2",
            "field3__in": [1, 2, 3],
            ...
        }
        """
        if not filters:
            return queryset

        try:
            return queryset.filter(**filters)
        except Exception:
            # Log the error or handle invalid filter fields
            return queryset

    @action(detail=False, methods=["post"])
    def bulk_update(self, request):
        """
        Update multiple instances in a single request with optional filtering

        Expected request format:
        {
            "ids": [1, 2, 3, ...],  # Optional if filters are provided
            "filters": {            # Optional if ids are provided
                "field1": "value1",
                "field2__contains": "value2",
                ...
            },
            "data": {
                "field1": "value1",
                "field2": "value2",
                ...
            }
        }
        """
        ids = request.data.get("ids", [])
        filters = request.data.get("filters", {})
        update_data = request.data.get("data", {})

        if not update_data:
            return Response(
                {"error": "'data' is required for bulk update"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not ids and not filters:
            return Response(
                {"error": "Either 'ids' or 'filters' must be provided for bulk update"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Run the requested changes through the ViewSet's serializer so
        # read_only_fields, write_only secrets, and mixins like
        # CompanyScopedSerializerMixin are enforced exactly as they would be
        # for a single PATCH -- queryset.update() has no other opportunity
        # to apply that field-level policy.
        update_data, error_response = self._sanitize_bulk_update_data(update_data)
        if error_response is not None:
            return error_response
        if not update_data:
            return Response(
                {"error": "No writable fields were provided for bulk update"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Start with the base queryset, narrowed to rows the user actually
        # has change (or change_own) permission on -- bulk operations must
        # not be able to touch more than get_object()/check_object_permissions
        # would allow one at a time.
        queryset = scope_queryset_to_permission(
            self.get_queryset(), request.user, "change", request=request
        )

        # Apply ID filtering if provided
        if ids:
            queryset = queryset.filter(id__in=ids)

        # Apply additional filters if provided
        if filters:
            queryset = self._apply_filters_to_queryset(queryset, filters)

        # Check if any records match the criteria
        record_count = queryset.count()
        if record_count == 0:
            return Response(
                {"error": "No records match the provided criteria"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Perform bulk update within a transaction
        with transaction.atomic():
            updated_count = queryset.update(**update_data)

        return Response(
            {
                "message": f"Successfully updated {updated_count} records",
                "updated_count": updated_count,
            }
        )

    @action(detail=False, methods=["post"])
    def bulk_delete(self, request):
        """
        Delete multiple instances in a single request with optional filtering

        Expected request format:
        {
            "ids": [1, 2, 3, ...],  # Optional if filters are provided
            "filters": {            # Optional if ids are provided
                "field1": "value1",
                "field2__contains": "value2",
                ...
            }
        }

        Or for simple ID-based deletion:
        [1, 2, 3, ...]
        """
        # Handle direct array format for backward compatibility
        if isinstance(request.data, list):
            ids = request.data
            filters = {}
        else:
            ids = request.data.get("ids", [])
            filters = request.data.get("filters", {})

        if not ids and not filters:
            return Response(
                {"error": "Either 'ids' or 'filters' must be provided for bulk delete"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Start with the base queryset, narrowed to rows the user actually
        # has delete (or delete_own) permission on -- bulk operations must
        # not be able to touch more than get_object()/check_object_permissions
        # would allow one at a time.
        queryset = scope_queryset_to_permission(
            self.get_queryset(), request.user, "delete", request=request
        )

        # Apply ID filtering if provided
        if ids:
            queryset = queryset.filter(id__in=ids)

        # Apply additional filters if provided
        if filters:
            queryset = self._apply_filters_to_queryset(queryset, filters)

        # Check if any records match the criteria
        record_count = queryset.count()
        if record_count == 0:
            return Response(
                {"error": "No records match the provided criteria"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Perform bulk delete within a transaction
        with transaction.atomic():
            deleted_count, _ = queryset.delete()

        return Response(
            {
                "message": f"Successfully deleted {deleted_count} records",
                "deleted_count": deleted_count,
            }
        )
