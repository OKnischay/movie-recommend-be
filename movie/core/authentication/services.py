import datetime
from rest_framework import status
from rest_framework.response import Response
from authentication.serializers import ChangePasswordSerializer, ForgotPasswordSerializer, RegisterSerializer, LoginSerializer
from authentication.utils import get_tokens
from users.models import CustomUser as User
from rest_framework.exceptions import ValidationError
from urllib.parse import unquote, quote
from django.core.mail import send_mail
from django.core.signing import Signer
from django.utils import timezone
class Services:
    def register(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            tokens = get_tokens(user)

            data = {
                "id": str(user.id),
                "email": user.email,
                "role": user.role,
                "access_token": tokens[0],
                "refresh_token": tokens[1],
            }
            return Response(data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def login(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            tokens = get_tokens(user)

            data = {
                "id": str(user.id),
                "email": user.email,
                "role": user.role,
                "access_token": tokens[0],
                "refresh_token": tokens[1],
            }
            return Response(data, status=status.HTTP_200_OK)

        return Response({"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)



    def change_pw(self, payload):
        serializer = ChangePasswordSerializer(data=payload)

        if not serializer.is_valid():
            raise ValidationError(
                detail=serializer.errors,
                code=status.HTTP_400_BAD_REQUEST,
            )


        return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)


    # def forgot_password(self, request):
    #     try:
    #         token = unquote(request.get("token", ""))
    #         claims = Signer().unsign_object(token)
    #         exp, email = claims.get("exp"), claims.get("email")

    #         if exp and timezone.now() > datetime.datetime.fromisoformat(exp):
    #             return Response({"error": "token expired"}, status=status.HTTP_410_GONE)

    #         user = User.objects.filter(email=email).first()
    #         if not user:
    #             return Response({"error": "User with this email not found"}, status=status.HTTP_400_BAD_REQUEST)

    #         serializer = ForgotPasswordSerializer(data=request)
    #         serializer.is_valid(raise_exception=True)

    #         user.set_password(serializer.validated_data["password"])
    #         user.save()

    #         return Response("Password changed successfully", status.HTTP_200_OK)

    #     except Exception as e:
    #         return Response({"error": "Failed to reset passoword"}, status=status.HTTP_400_BAD_REQUEST)
            
        
    # def check_and_send_mail(self, request):
    #     try:
    #         email = request.get("email")
    #         user = User.objects.filter(email=email).first()
    #         if not user:
    #             return Response(
    #                 {"error": "Invalid email"},
    #                 status=status.HTTP_404_NOT_FOUND
    #             )

    #         claims = {
    #             "email": email,
    #             "iat": timezone.now().isoformat(),
    #             "exp": (timezone.now() + timezone.timedelta(minutes=15)).isoformat(),
    #         }
    #         signer = Signer()
    #         token = signer.sign_object(claims)
    #         token = quote(token)  

    #         reset_link = f"http://localhost:3000/forgot/password/{token}/"

    #         send_mail(
    #             subject="Password Reset Request",
    #             message=(
    #                 f"Hello,\n\nWe received a request to reset your password. Please click the link below to reset it:\n\n"
    #                 f"{reset_link}\n\n"
    #                 "If you didn't request a password reset, please ignore this email. Your password will remain unchanged.\n\n"
    #                 "Best regards,\nCineMatch"
    #             ),
    #             from_email="nischaybasi015@gmail.com",
    #             recipient_list=[email],
    #             fail_silently=False,
    #         )

    #         return Response(
    #             {"message": "Password reset link sent successfully"},
    #             status=status.HTTP_200_OK
    #         )

    #     except Exception as e:
    #         return Response(
    #             {"error": str(e), "message": "Failed to send password reset link"},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )

    def forgot_password(self, request):
        try:
            token = unquote(request.data.get("token", ""))
            claims = Signer().unsign_object(token)
            exp, email = claims.get("exp"), claims.get("email")

            if exp and timezone.now() > datetime.datetime.fromisoformat(exp):
                return Response({"error": "Token has expired"}, status=status.HTTP_400_BAD_REQUEST)

            user = User.objects.filter(email=email).first()
            if not user:
                return Response({"error": "User with this email not found"}, status=status.HTTP_400_BAD_REQUEST)

            serializer = ForgotPasswordSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            user.set_password(serializer.validated_data["password"])
            user.save()

            return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {"error": str(e), "message": "Failed to reset password"},
                status=status.HTTP_400_BAD_REQUEST
            )

    def check_and_send_mail(self, request):
        try:
            email = request.data.get("email")
            user = User.objects.filter(email=email).first()
            if not user:
                return Response({"error": "Invalid email"}, status=status.HTTP_400_BAD_REQUEST)

            claims = {
                "email": email,
                "iat": timezone.now().isoformat(),
                "exp": (timezone.now() + timezone.timedelta(minutes=15)).isoformat(),
            }
            signer = Signer()
            token = signer.sign_object(claims)
            token = quote(token)

            reset_link = f"http://localhost:3000/forgotpassword/{token}/"

            send_mail(
                subject="Password Reset Request",
                message=(
                    f"Hello,\n\nWe received a request to reset your password. Please click the link below to reset it:\n\n"
                    f"{reset_link}\n\n"
                    "If you didn't request a password reset, please ignore this email.\n\n"
                    "Best regards,\nCineMatch"
                ),
                from_email="nischaybasi015@gmail.com",
                recipient_list=[email],
                fail_silently=False,
            )

            return Response(
                {"message": "Password reset link sent successfully"},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {"error": str(e), "message": "Failed to send password reset link"},
                status=status.HTTP_400_BAD_REQUEST
            )
