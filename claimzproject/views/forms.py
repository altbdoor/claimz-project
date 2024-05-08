from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Button, Div, Field, Layout, Reset, Submit
from django import forms
from django.contrib.auth import get_user_model
from django.db.models.fields import BLANK_CHOICE_DASH
from django.forms.fields import DateField
from django.urls import reverse_lazy

from claims.models import Claims, ClaimsCategory, ClaimsLogs

User = get_user_model()


class BackButton(Button):
    field_classes = "btn btn-outline-secondary"

    def __init__(self, value="Go back"):
        alpine_attr = {
            "x-on:click.prevent": "history.back()",
        }

        super().__init__("_back", value, **alpine_attr)


class ResetButton(Button):
    field_classes = "btn btn-outline-secondary"
    input_type = "reset"

    def __init__(self, value="Reset"):
        alpine_attr = {
            "x-on:click.prevent": "location = location.pathname",
        }

        super().__init__("_reset", value, **alpine_attr)


class PlainSubmit(Submit):
    field_classes = "btn"


# ========================================
class CrispyForm:
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.attrs.update({"x-init": ""})
        self.helper.add_input(BackButton())
        self.helper.add_input(Submit("_submit", "Submit"))

        super().__init__(*args, **kwargs)


# ========================================
BaseClaimsForm = forms.modelform_factory(
    Claims,
    fields=(
        "invoice_id",
        "invoice_date",
        "category",
        "amount",
        "description",
        "invoice_file",
        "status",
    ),
    labels={
        "invoice_id": "Invoice ID",
        "amount": "Amount (MYR)",
    },
    widgets={
        "invoice_id": forms.TextInput(),
        # "invoice_date": forms.SelectDateWidget()
        "invoice_date": forms.DateInput(attrs={"type": "date"}),
    },
)


class ClaimsForm(CrispyForm, BaseClaimsForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        del self.fields["status"]
        self.fields["category"].queryset = self.fields["category"].queryset.filter(
            is_active=True
        )

        today = date.today()
        invoice_date_field: DateField = self.fields["invoice_date"]
        invoice_date_field.initial = today

        if isinstance(invoice_date_field.widget, forms.SelectDateWidget):
            invoice_date_field.widget.years = range(today.year - 1, today.year + 1)

        elif isinstance(invoice_date_field.widget, forms.DateInput):
            invoice_date_field.widget.attrs.update(
                {
                    "max": today.isoformat(),
                    "min": today.replace(year=today.year - 1).isoformat(),
                }
            )

    def clean_amount(self):
        amount: Decimal = self.cleaned_data.get("amount")
        if amount <= 0:
            raise forms.ValidationError("Amount must be more than zero")

        return amount

    def clean_invoice_date(self):
        invoice_date: date = self.cleaned_data.get("invoice_date")
        today = date.today()

        if invoice_date > today:
            raise forms.ValidationError("Invoice date cannot be in the future.")

        return invoice_date


class SearchClaimsForm(BaseClaimsForm):
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_method = "get"
        self.helper.attrs.update({"x-init": ""})
        self.helper.layout = Layout(
            Div(
                Div(
                    Field("invoice_id"),
                    css_class="col-md-4",
                ),
                Div(
                    Field("category"),
                    css_class="col-md-4",
                ),
                Div(
                    Field("status"),
                    css_class="col-md-4",
                ),
                css_class="row",
            ),
        )
        self.helper.add_input(ResetButton())
        self.helper.add_input(Submit("_filter", "Filter"))

        super().__init__(*args, **kwargs)

        only_show_fields = ("invoice_id", "category", "status")
        for field_name in list(self.fields.keys()):
            if field_name in only_show_fields:
                self.fields[field_name].required = False
            else:
                del self.fields[field_name]

        self.fields["status"].initial = ""
        self.fields["status"].choices = (
            BLANK_CHOICE_DASH + self.fields["status"].choices
        )


class AdminSearchClaimsForm(SearchClaimsForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        del self.fields["status"]

        self.helper.layout = Layout(
            Div(
                Div(
                    Field("invoice_id"),
                    css_class="col-md-6",
                ),
                Div(
                    Field("category"),
                    css_class="col-md-6",
                ),
                css_class="row",
            ),
        )


class AdminReportClaimsForm(forms.Form):
    start_date = forms.DateTimeField(widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateTimeField(widget=forms.DateInput(attrs={"type": "date"}))
    created_by = forms.ModelChoiceField(
        queryset=User.objects.all().order_by("username")
    )
    category = forms.ModelChoiceField(queryset=ClaimsCategory.objects.all())

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.attrs.update({"x-init": ""})
        self.helper.form_method = "get"
        self.helper.layout = Layout(
            Div(
                Div(
                    Field("start_date"),
                    css_class="col-md-6",
                ),
                Div(
                    Field("end_date"),
                    css_class="col-md-6",
                ),
                Div(
                    Field("created_by"),
                    css_class="col-md-6",
                ),
                Div(
                    Field("category"),
                    css_class="col-md-6",
                ),
                css_class="row",
            ),
        )
        self.helper.add_input(ResetButton())
        self.helper.add_input(Submit("_filter", "Filter"))
        self.helper.add_input(
            PlainSubmit("_export", "Export as CSV", css_class="btn-outline-primary")
        )

        super().__init__(*args, **kwargs)

        for field_name in self.fields.keys():
            self.fields[field_name].required = False

        today = datetime.today().replace(tzinfo=timezone.utc)
        _, last_day = monthrange(today.year, today.month)
        self.fields["start_date"].initial = today.replace(
            day=1, hour=0, minute=0, second=0
        )
        self.fields["end_date"].initial = today.replace(
            day=last_day, hour=23, minute=59, second=59
        )

    def clean_start_date(self):
        val: datetime = self.cleaned_data.get("start_date")
        if not val:
            return None

        return val.replace(tzinfo=timezone.utc, hour=0, minute=0, second=0)

    def clean_end_date(self):
        val: datetime = self.cleaned_data.get("end_date")
        if not val:
            return None

        return val.replace(tzinfo=timezone.utc, hour=23, minute=59, second=59)


# ========================================
BaseClaimsCategory = forms.modelform_factory(
    ClaimsCategory,
    fields=(
        "name",
        "description",
        "is_active",
    ),
    labels={"is_active": "Is active?"},
    widgets={
        "name": forms.TextInput(),
    },
)


class ClaimsCategoryForm(CrispyForm, BaseClaimsCategory):
    pass


# ========================================
BaseClaimLogsForm = forms.modelform_factory(
    ClaimsLogs,
    fields=("remarks",),
    labels={
        "remarks": "Add optional remarks for the action",
    },
)


class ActionClaimsForm(BaseClaimLogsForm):
    def __init__(self, action="", *args, **kwargs):
        self.helper = FormHelper()
        self.helper.attrs.update({"x-init": ""})

        self.helper.add_input(BackButton())
        if action == "approve":
            self.helper.add_input(Submit("_submit", "Approve", css_class="btn-success"))
        elif action == "reject":
            self.helper.add_input(Submit("_submit", "Reject", css_class="btn-danger"))
        elif action == "finalize":
            self.helper.add_input(
                Submit("_submit", "Finalize", css_class="btn-primary")
            )

        super().__init__(*args, **kwargs)
        self.fields.get("remarks").required = False
