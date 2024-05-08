from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.contrib.auth.views import LoginView as BaseLoginView
from django.contrib.auth.views import LogoutView as BaseLogoutView
from django.core.paginator import Page
from django.http import HttpRequest, HttpResponse
from django.utils.functional import cached_property
from django.views.generic.edit import FormMixin
from django.views.generic.list import ListView


# Create your views here.
class LoginView(BaseLoginView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["form"].helper = FormHelper()
        context["form"].helper.form_action = "login"
        context["form"].helper.add_input(Submit("submit", "Submit"))

        return context


class LogoutView(BaseLogoutView):
    http_method_names = ["get", "post", "options"]

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        return self.post(request, *args, **kwargs)


# https://stackoverflow.com/a/7012420
class FilterSortListView(FormMixin, ListView):
    allowed_filters = {}
    filter_names = ("_filter",)

    @cached_property
    def is_filter_active(self):
        for name in self.filter_names:
            if name in self.request.GET.keys():
                return True

        return False

    @cached_property
    def _get_filters_from_form(self):
        form_instance = self.get_form()
        is_form_valid = form_instance.is_valid()

        qs_filters = {}
        form_value = {}

        for query_param, queryset_name in self.allowed_filters.items():
            query_val = form_instance.fields.get(query_param).initial
            if is_form_valid:
                query_val = form_instance.cleaned_data.get(query_param)

            form_value.setdefault(query_param, None)

            if query_val:
                qs_filters[queryset_name] = query_val
                form_value[query_param] = query_val

        return qs_filters, form_value

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        if self.is_filter_active:
            kwargs.update(
                {
                    "data": self.request.GET,
                    "files": None,
                }
            )

        return kwargs

    def get_queryset(self):
        qs = super().get_queryset()
        additional_filters, _ = self._get_filters_from_form

        if len(additional_filters.keys()) > 0:
            qs = qs.filter(**additional_filters)

        # if "order_by" in self.request.GET:
        #     queryset = queryset.order_by(self.request.GET["order_by"])

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_form"] = context.pop("form")

        query_copy = self.request.GET.copy()
        page_obj: Page = context["page_obj"]

        query_copy["page"] = 1
        context["first_page_url"] = query_copy.urlencode()

        query_copy["page"] = page_obj.paginator.num_pages
        context["last_page_url"] = query_copy.urlencode()

        context["next_page_url"] = ""
        context["previous_page_url"] = ""

        if page_obj.has_next():
            query_copy["page"] = page_obj.next_page_number()
            context["next_page_url"] = query_copy.urlencode()

        if page_obj.has_previous():
            query_copy["page"] = page_obj.previous_page_number()
            context["previous_page_url"] = query_copy.urlencode()

        return context
