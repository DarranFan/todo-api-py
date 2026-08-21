from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    ChangePasswordView,
    LogoutView,
    TaskViewSet,
    UserRegistrationView,
)


router = DefaultRouter()
router.register("categories", CategoryViewSet)
router.register("tasks", TaskViewSet)

urlpatterns = [
    path("register/", UserRegistrationView.as_view(), name="register"),
    path(
        "change-password/",
        ChangePasswordView.as_view(),
        name="change-password",
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
] + router.urls
