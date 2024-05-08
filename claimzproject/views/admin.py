import csv
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Avg, Count, Sum
from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import DetailView, UpdateView

from claims.const import PERM_CAN_ADMIN_CLAIMS
from claims.models import Claims, ClaimsCategory
from claimzproject.views.auth import FilterSortListView

from .forms import ActionClaimsForm, AdminReportClaimsForm, AdminSearchClaimsForm

User = get_user_model()
VIEW_CAN_ADMIN_CLAIMS = f"claims.{PERM_CAN_ADMIN_CLAIMS}"


class BaseAdminView(LoginRequiredMixin, PermissionRequiredMixin):
    permission_required = [VIEW_CAN_ADMIN_CLAIMS]


class AdminDetailClaimsView(BaseAdminView, DetailView):
    template_name = "dashboard/detail-claims.html"
    model = Claims


class AdminListClaimsView(BaseAdminView, FilterSortListView):
    template_name = "admin/list-claims.html"
    model = Claims
    paginate_by = 20
    status = ""

    form_class = AdminSearchClaimsForm
    allowed_filters = {
        "invoice_id": "invoice_id__icontains",
        "category": "category",
    }

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        self.status = kwargs.get("status", "")
        if self.status not in ("open", "rejected", "finalized"):
            return self.http_method_not_allowed(request, *args, **kwargs)

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("logs").order_by("-modified")

        if self.status == "open":
            qs = qs.filter(
                status__in=(
                    Claims.StatusChoice.OPEN,
                    Claims.StatusChoice.IN_PROGRESS,
                )
            )
        elif self.status == "rejected":
            qs = qs.filter(status=Claims.StatusChoice.REJECTED)
        elif self.status == "finalized":
            qs = qs.filter(status=Claims.StatusChoice.APPROVED)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status"] = self.status
        return context


class AdminActionClaimsView(BaseAdminView, UpdateView):
    model = Claims
    template_name = "admin/action-claims.html"
    form_class = ActionClaimsForm
    action = ""

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        self.action = kwargs.get("action", "")
        if self.action not in ("approve", "reject", "finalize"):
            return self.http_method_not_allowed(request, *args, **kwargs)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["action"] = self.action
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["action"] = self.action
        return kwargs

    def form_valid(self, form: ActionClaimsForm) -> HttpResponse:
        claim: Claims = self.get_object()
        remarks = form.cleaned_data.get("remarks", "")

        handler = getattr(claim, self.action)
        handler(self.request.user.pk, remarks)

        redirect_url = reverse("admin-list-claims", kwargs={"status": "open"})
        if self.action == "reject":
            redirect_url = reverse("admin-list-claims", kwargs={"status": "rejected"})
        elif self.action == "finalize":
            redirect_url = reverse("admin-list-claims", kwargs={"status": "finalized"})

        return redirect(redirect_url)


class AdminReportsView(BaseAdminView, FilterSortListView):
    template_name = "admin/report.html"
    model = Claims
    paginate_by = 20
    ordering = ("-modified",)

    form_class = AdminReportClaimsForm
    allowed_filters = {
        "start_date": "modified__gte",
        "end_date": "modified__lte",
        "created_by": "created_by",
        "category": "category",
    }
    filter_names = (
        "_filter",
        "_export",
    )

    def get_queryset(self):
        qs = super().get_queryset().filter(status=Claims.StatusChoice.APPROVED)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["meta"] = self.get_queryset().aggregate(
            sum=Sum("amount", default=0),
            average=Avg("amount", default=0),
            count=Count("amount"),
        )

        return context

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if "_export" not in request.GET.keys():
            return super().get(request, *args, **kwargs)

        _, form_value = self._get_filters_from_form

        if form_value["start_date"]:
            form_value["start_date"] = form_value["start_date"].isoformat()

        if form_value["end_date"]:
            form_value["end_date"] = form_value["end_date"].isoformat()

        if form_value["created_by"]:
            form_value["created_by"] = form_value["created_by"].get_username()

        if form_value["category"]:
            form_value["category"] = form_value["category"].name

        def stream_data():
            yield csv_row_generator(("Start date", form_value["start_date"]))
            yield csv_row_generator(("End date", form_value["end_date"]))
            yield csv_row_generator(("Created by", form_value["created_by"]))
            yield csv_row_generator(("Category", form_value["category"]))

            yield csv_row_generator(
                (
                    "ID",
                    "Invoice ID",
                    "Invoice date",
                    "Category",
                    "Created by",
                    "Created on",
                    "Approved on",
                    "Amount",
                )
            )

            claims: list[Claims] = self.get_queryset()
            for obj in claims:
                yield csv_row_generator(
                    (
                        obj.pk,
                        obj.invoice_id,
                        obj.invoice_date.isoformat(),
                        obj.category.name,
                        obj.created_by.username,
                        obj.created.isoformat(),
                        obj.modified.isoformat(),
                        obj.amount,
                    )
                )

        response = StreamingHttpResponse(stream_data(), content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=export.csv"
        return response


def csv_row_generator(row: list):
    """
    Generates a CSV row and returns its value as a string.
    """
    csvfile = StringIO()
    csvwriter = csv.writer(csvfile)
    csvwriter.writerow(row)
    return csvfile.getvalue()
