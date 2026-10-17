# `finlo_apps.py`

## 🎯 Purpose

This file extends `INSTALLED_APPS` beyond what is defined in `base.py`.

It does:
- imports `INSTALLED_APPS` from `finlo.settings.base`
- appends Finlo/CRM app packages (accounts, contacts, leads, etc.)

## What it adds (current)

It extends with:
- `finlo_crm.accounts`
- `finlo_crm.contacts`
- `finlo_crm.leads`
- `finlo_crm.scoring_rules`
- `finlo_crm.campaigns`
- `finlo_crm.opportunities`
- `finlo_crm.forecast`
- `booking`

`booking` is documented in [../contrib/booking/booking.md](../contrib/booking/booking.md).

## When it runs

It is loaded automatically when:
- Django imports `finlo.settings.__init__`
- that file imports `finlo.settings.finlo_apps` **after** `base` and **before** `local_settings`

So CRM apps are registered before local overrides apply. See [local_settings.md](local_settings.md) for the full load order.
