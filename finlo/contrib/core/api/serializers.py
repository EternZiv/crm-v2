"""
Serializers for core models
"""

# Third-party imports (Django)
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

# First party imports (Finlo)
from finlo.api.mixins import CompanyScopedSerializerMixin
from finlo.contrib.core.authorization import get_company_scope
from finlo.auth.models import User
from finlo.core.exceptions import ValidationError

# Local imports
from ..models import (
    BusinessHour,
    Company,
    CustomerRole,
    Department,
    Holiday,
    FinloAttachment,
    ImportHistory,
    PartnerRole,
    Role,
    SalesAssignment,
    SalesRegion,
    SalesTeam,
    TeamRole,
)


class CompanySerializer(serializers.ModelSerializer):
    """Serializer for Company model"""

    class Meta:
        """Meta class for CompanySerializer"""

        model = Company
        fields = "__all__"


class DepartmentSerializer(CompanyScopedSerializerMixin, serializers.ModelSerializer):
    """Serializer for Department model"""

    class Meta:
        """Meta class for DepartmentSerializer"""

        model = Department
        fields = "__all__"


class RoleSerializer(CompanyScopedSerializerMixin, serializers.ModelSerializer):
    """Serializer for Role model"""

    class Meta:
        """Meta class for RoleSerializer"""

        model = Role
        fields = "__all__"
        read_only_fields = ["system_key"]


class SalesRegionSerializer(
    CompanyScopedSerializerMixin, serializers.ModelSerializer
):
    class Meta:
        model = SalesRegion
        fields = "__all__"
        read_only_fields = ["created_at", "created_by", "updated_at", "updated_by"]


class SalesTeamSerializer(CompanyScopedSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = SalesTeam
        fields = "__all__"
        read_only_fields = ["created_at", "created_by", "updated_at", "updated_by"]


class SalesAssignmentSerializer(
    CompanyScopedSerializerMixin, serializers.ModelSerializer
):
    class Meta:
        model = SalesAssignment
        fields = "__all__"
        read_only_fields = ["created_at", "created_by", "updated_at", "updated_by"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = self.instance
        if instance is None:
            instance = SalesAssignment(**attrs)
        else:
            for field, value in attrs.items():
                setattr(instance, field, value)
        try:
            instance.full_clean()
        except ValidationError as error:
            raise serializers.ValidationError(
                getattr(error, "message_dict", error.messages)
            ) from error
        return attrs


class FinloUserSerializer(serializers.ModelSerializer):
    """Serializer for FinloUser model"""

    class Meta:
        """Meta class for FinloUserSerializer"""

        model = User
        fields = "__all__"
        # is_superuser/is_staff/user_permissions/groups must never be
        # settable through ordinary add_user/change_user permission --
        # the classic (non-DRF) user form already excludes these same
        # fields (finlo/contrib/core/forms/users.py UserFormClass.Meta.exclude)
        # so that granting someone "add user" or "change user" cannot be
        # used to mint or promote a superuser account.
        read_only_fields = [
            "is_superuser",
            "is_staff",
            "user_permissions",
            "groups",
            "last_login",
            "date_joined",
        ]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        """Create and return a user with the given validated data."""
        request = self.context.get("request")
        actor = getattr(request, "user", None)
        if actor and not actor.is_superuser:
            scope = get_company_scope(actor, request)
            if scope.company_id is None:
                raise serializers.ValidationError(
                    {"company": "Your account is not assigned to a company."}
                )
            validated_data["company_id"] = scope.company_id

        password = validated_data.get("password")
        if password:
            try:
                validate_password(password)
            except ValidationError as e:
                raise serializers.ValidationError({"password": e.messages})
        user = User.objects.create_user(**validated_data)
        return user

    def validate(self, attrs):
        """Prevent non-administrators from moving users or granting roles."""
        attrs = super().validate(attrs)
        request = self.context.get("request")
        actor = getattr(request, "user", None)
        if actor is None or not actor.is_authenticated or actor.is_superuser:
            target_company = attrs.get(
                "company", getattr(self.instance, "company", None)
            )
        else:
            scope = get_company_scope(actor, request)
            if self.instance is None:
                target_company_id = scope.company_id
            else:
                target_company_id = self.instance.company_id

            if target_company_id is None or target_company_id != scope.company_id:
                raise serializers.ValidationError(
                    {"company": "You cannot manage users outside your active company."}
                )
            if "company" in attrs:
                supplied_company = attrs["company"]
                if (
                    supplied_company is None
                    or supplied_company.pk != target_company_id
                ):
                    raise serializers.ValidationError(
                        {"company": "You cannot assign a user to another company."}
                    )
            target_company = attrs.get("company")
            if target_company is None:
                target_company = getattr(self.instance, "company", None)
            if target_company is None:
                target_company = Company.objects.filter(
                    pk=target_company_id
                ).first()
                if target_company is None:
                    raise serializers.ValidationError(
                        {"company": "Your active company could not be found."}
                    )

            requested_role = attrs.get("role")
            current_role = getattr(self.instance, "role", None)
            if requested_role is not None and requested_role != current_role:
                if not actor.has_perm("core.change_role"):
                    raise serializers.ValidationError(
                        {"role": "You do not have permission to assign roles."}
                    )

        for field_name in ("role", "department", "currency"):
            related = attrs.get(field_name)
            if related is not None:
                if (
                    target_company is None
                    or getattr(related, "company_id", None) != target_company.pk
                ):
                    raise serializers.ValidationError(
                        {field_name: "This value must belong to the user's company."}
                    )

        return attrs

    def update(self, instance, validated_data):
        """Update user; set password via set_password if provided."""
        if "password" in validated_data:
            password = validated_data.pop("password")
            try:
                validate_password(password, user=instance)
            except ValidationError as e:
                raise serializers.ValidationError({"password": e.messages})
            instance.set_password(password)
        return super().update(instance, validated_data)


class BusinessHourSerializer(CompanyScopedSerializerMixin, serializers.ModelSerializer):
    """Serializer for BusinessHour model"""

    class Meta:
        """Meta class for BusinessHourSerializer"""

        model = BusinessHour
        fields = "__all__"


class TeamRoleSerializer(CompanyScopedSerializerMixin, serializers.ModelSerializer):
    """Serializer for TeamRole model"""

    class Meta:
        """Meta class for TeamRoleSerializer"""

        model = TeamRole
        fields = "__all__"


class CustomerRoleSerializer(CompanyScopedSerializerMixin, serializers.ModelSerializer):
    """Serializer for CustomerRole model"""

    class Meta:
        """Meta class for CustomerRoleSerializer"""

        model = CustomerRole
        fields = "__all__"


class PartnerRoleSerializer(CompanyScopedSerializerMixin, serializers.ModelSerializer):
    """Serializer for PartnerRole model"""

    class Meta:
        """Meta class for PartnerRoleSerializer"""

        model = PartnerRole
        fields = "__all__"


class ImportHistorySerializer(
    CompanyScopedSerializerMixin, serializers.ModelSerializer
):
    """Serializer for ImportHistory model"""

    class Meta:
        """Meta class for ImportHistorySerializer"""

        model = ImportHistory
        fields = "__all__"


class FinloAttachmentSerializer(
    CompanyScopedSerializerMixin, serializers.ModelSerializer
):
    """Serializer for FinloAttachment model"""

    class Meta:
        """Meta class for FinloAttachmentSerializer"""

        model = FinloAttachment
        fields = "__all__"


class HolidaySerializer(CompanyScopedSerializerMixin, serializers.ModelSerializer):
    """Serializer for Holiday model"""

    class Meta:
        """Meta class for HolidaySerializer"""

        model = Holiday
        fields = "__all__"
