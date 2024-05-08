from typing import cast

from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, UpdateView
from django.views.generic.base import TemplateView
from django.views.generic.list import ListView

from claims.const import PERM_CAN_EDIT_CLAIMS_CATEGORY
from claims.models import Claims, ClaimsCategory

from .auth import FilterSortListView
from .forms import ClaimsCategoryForm, ClaimsForm, SearchClaimsForm


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/home.html"


# ========================================
class CreateClaimsView(LoginRequiredMixin, CreateView):
    template_name = "dashboard/base-create-view.html"
    model = Claims
    form_class = ClaimsForm
    success_url = reverse_lazy("list-claims")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Create new claim"
        return context


class EditClaimsView(UserPassesTestMixin, LoginRequiredMixin, UpdateView):
    template_name = "dashboard/base-create-view.html"
    model = Claims
    form_class = ClaimsForm
    success_url = reverse_lazy("list-claims")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj_item: Claims = context["object"]
        context["page_title"] = f"Edit claim {obj_item}"
        return context

    def test_func(self) -> bool:
        return cast(Claims, self.get_object()).created_by == self.request.user


class DetailClaimsView(UserPassesTestMixin, LoginRequiredMixin, DetailView):
    template_name = "dashboard/detail-claims.html"
    model = Claims

    def test_func(self) -> bool:
        return cast(Claims, self.get_object()).created_by == self.request.user


class DuplicateClaimsView(DetailClaimsView):
    template_name = "dashboard/duplicate-claims.html"
    model = Claims

    def post(self, request: HttpRequest, *args, **kwargs):
        obj: Claims = self.get_object()
        new_obj = obj.duplicate()
        return redirect(reverse("edit-claims", kwargs={"pk": new_obj.pk}))


class ListClaimsView(LoginRequiredMixin, FilterSortListView):
    template_name = "dashboard/list-claims.html"
    model = Claims
    paginate_by = 20
    form_class = SearchClaimsForm
    allowed_filters = {
        "invoice_id": "invoice_id__icontains",
        "category": "category",
        "status": "status",
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(created_by=self.request.user)


class DeleteClaimsView(UserPassesTestMixin, LoginRequiredMixin, DeleteView):
    template_name = "dashboard/delete-claims.html"
    model = Claims
    success_url = reverse_lazy("list-claims")

    def test_func(self) -> bool:
        obj: Claims = self.get_object()
        if obj.created_by != self.request.user:
            return False
        elif obj.status != Claims.StatusChoice.OPEN:
            return False

        return True


# ========================================
VIEW_CAN_EDIT_CLAIMS_CATEGORY = f"claims.{PERM_CAN_EDIT_CLAIMS_CATEGORY}"


class CreateClaimsCategoryView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    template_name = "dashboard/base-create-view.html"
    model = ClaimsCategory
    form_class = ClaimsCategoryForm
    success_url = reverse_lazy("list-claims-category")
    permission_required = [VIEW_CAN_EDIT_CLAIMS_CATEGORY]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Create new category"
        return context


class EditClaimsCategoryView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    template_name = "dashboard/base-create-view.html"
    model = ClaimsCategory
    form_class = ClaimsCategoryForm
    success_url = reverse_lazy("list-claims-category")
    permission_required = [VIEW_CAN_EDIT_CLAIMS_CATEGORY]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj_item: Claims = context["object"]
        context["page_title"] = f"Edit {obj_item} category"
        return context


class ListClaimsCategoryView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    template_name = "dashboard/claims-category-list.html"
    paginate_by = 20
    model = ClaimsCategory
    permission_required = [VIEW_CAN_EDIT_CLAIMS_CATEGORY]
