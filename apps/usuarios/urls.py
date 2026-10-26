"""Rutas de autenticación y usuarios."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from apps.usuarios.views import (
    AgaAuthLoginView,
    LoginView,
    LogoutView,
    MeView,
    PasswordChangeView,
    RoleDefinitionViewSet,
    RoleListView,
    UserViewSet,
)

app_name = "usuarios"

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("role-definitions", RoleDefinitionViewSet, basename="role-definition")

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("login/aga/", AgaAuthLoginView.as_view(), name="login_aga"),
    path("token/", LoginView.as_view(), name="token_obtain"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("password/change/", PasswordChangeView.as_view(), name="password_change"),
    path("roles/", RoleListView.as_view(), name="roles"),
    path("", include(router.urls)),
]
