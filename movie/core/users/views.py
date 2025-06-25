# apps/users/views.py

from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import CustomUser
from users.selectors import get_user_by_id, get_all_users
from users.services import update_user_profile
from users.serializers import (
    UserSerializer,
    UserDetailSerializer,
    UserUpdateSerializer,
)

class UserListView(generics.ListAPIView):
    queryset = get_all_users()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]

class UserDetailView(generics.RetrieveAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

class UserUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        user = request.user
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserDetailSerializer(user).data)
