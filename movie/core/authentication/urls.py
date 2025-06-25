# users/urls.py
from django.urls import path
from authentication.views import ChangePasswordView, RegisterView, LoginView

urlpatterns = [
    path("signup/", RegisterView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("password/change/", ChangePasswordView.as_view(), name="change-password"),
]
