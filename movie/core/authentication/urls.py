# users/urls.py
from django.urls import path
from authentication.views import ChangePasswordView, RegisterView, LoginView, ForgotPasswordView, CheckAndSendMail

urlpatterns = [
    path("signup/", RegisterView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("password/change/", ChangePasswordView.as_view(), name="change-password"),
    path("password/forgot/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("password/forgot/mail/", CheckAndSendMail.as_view(), name="forgot-send-mail"),
]
