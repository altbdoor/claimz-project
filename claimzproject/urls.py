"""
URL configuration for claimzproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin as django_admin
from django.urls import path
from django.views.generic.base import TemplateView

from .views import admin, auth, dashboard

urlpatterns = [
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("login/", auth.LoginView.as_view(), name="login"),
    path("logout/", auth.LogoutView.as_view(), name="logout"),
    path("admin/", django_admin.site.urls),
    path("dashboard/", dashboard.HomeView.as_view(), name="dashboard"),
]

urlpatterns += [
    path("dashboard/claims/", dashboard.ListClaimsView.as_view(), name="list-claims"),
    path(
        "dashboard/claims/create/",
        dashboard.CreateClaimsView.as_view(),
        name="create-claims",
    ),
    path(
        "dashboard/claims/edit/<int:pk>/",
        dashboard.EditClaimsView.as_view(),
        name="edit-claims",
    ),
    path(
        "dashboard/claims/view/<int:pk>/",
        dashboard.DetailClaimsView.as_view(),
        name="detail-claims",
    ),
    path(
        "dashboard/claims/delete/<int:pk>/",
        dashboard.DeleteClaimsView.as_view(),
        name="delete-claims",
    ),
    path(
        "dashboard/claims/duplicate/<int:pk>/",
        dashboard.DuplicateClaimsView.as_view(),
        name="duplicate-claims",
    ),
]

urlpatterns += [
    path(
        "dashboard/claims-category/",
        dashboard.ListClaimsCategoryView.as_view(),
        name="list-claims-category",
    ),
    path(
        "dashboard/claims-category/create/",
        dashboard.CreateClaimsCategoryView.as_view(),
        name="create-claims-category",
    ),
    path(
        "dashboard/claims-category/edit/<int:pk>/",
        dashboard.EditClaimsCategoryView.as_view(),
        name="edit-claims-category",
    ),
]

urlpatterns += [
    path(
        "dashboard/admin/claims/reports/",
        admin.AdminReportsView.as_view(),
        name="admin-report-claims",
    ),
    path(
        "dashboard/admin/claims/action/<int:pk>/<str:action>/",
        admin.AdminActionClaimsView.as_view(),
        name="admin-action-claims",
    ),
    path(
        "dashboard/admin/claims/view/<int:pk>/",
        admin.AdminDetailClaimsView.as_view(),
        name="admin-detail-claims",
    ),
    path(
        "dashboard/admin/claims/<str:status>/",
        admin.AdminListClaimsView.as_view(),
        name="admin-list-claims",
    ),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
