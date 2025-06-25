
from rest_framework import status
from rest_framework.response import Response
from authentication.serializers import ChangePasswordSerializer, RegisterSerializer, LoginSerializer
from authentication.utils import get_tokens
from users.models import CustomUser as User
from rest_framework.exceptions import ValidationError

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

