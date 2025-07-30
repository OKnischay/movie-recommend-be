# users/views.py
from rest_framework.views import APIView
from authentication.services import Services

class RegisterView(APIView):
    def post(self, request):
        return Services().register(request)

class LoginView(APIView):
    def post(self, request):
        return Services().login(request)

class ChangePasswordView(APIView):
    def post(self, request):
        response = Services().change_pw(payload=request.data)
        return response

class ForgotPasswordView(APIView):
    def post(self, request):
        return Services().forgot_password(request)
    
class CheckAndSendMail(APIView):
    def post(self, request):
        return Services().check_and_send_mail(request)