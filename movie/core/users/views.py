# apps/users/views.py

from django.utils import timezone 
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
    UserStatusSerializer,
)

class UserListView(generics.ListAPIView):
    queryset = get_all_users()
    serializer_class = UserSerializer
    # permission_classes = [permissions.IsAdminUser]

class UserDetailView(generics.RetrieveAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserDetailSerializer
    # permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

class UserUpdateView(APIView):
    # permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        user = request.user
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserDetailSerializer(user).data)
class UserStatusUpdateView(APIView):
    # permission_classes = [permissions.IsAdminUser]
    
    def patch(self, request, id, *args, **kwargs):
        try:
            user = CustomUser.objects.get(id=id)
            new_status = request.data.get('status')
            
            if new_status == 'active':
                user.is_active = True
            elif new_status == 'inactive':
                user.is_active = False
            elif new_status == 'suspended':
                # For suspended users, we can set is_active to False
                # and maybe add a suspended field later if needed
                user.is_active = False
            else:
                return Response({'error': 'Invalid status'}, status=400)
                
            user.save()
            return Response({'message': 'User status updated successfully'})
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

# class UserDeleteView(APIView):
#     # permission_classes = [permissions.IsAdminUser]
    
#     def delete(self, request, id, *args, **kwargs):
#         try:
#             user = CustomUser.objects.get(id=id)
#             user.delete()
#             return Response({'message': 'User deleted successfully'})
#         except CustomUser.DoesNotExist:
#             return Response({'error': 'User not found'}, status=404)


class UserDeleteView(APIView):
    def delete(self, request, id, *args, **kwargs):
        try:
            user = CustomUser.objects.get(id=id, is_deleted=False)
            user.soft_delete()
            return Response({
                'message': 'User deactivated successfully',
                'deleted_at': user.deleted_at,
                'status': user.status,
                'is_active': user.is_active
            }, status=200)
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found or already deactivated'}, status=404)

class UserRestoreView(APIView):
    def post(self, request, id, *args, **kwargs):
        try:
            user = CustomUser.objects.with_deleted().get(id=id, is_deleted=True)
            user.restore()
            return Response({
                'message': 'User reactivated successfully',
                'restored_at': timezone.now(),
                'status': user.status,
                'is_active': user.is_active
            }, status=200)
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found or not deactivated'}, status=404)

class UserWithStatusListView(generics.ListAPIView):
    serializer_class = UserStatusSerializer
    # permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        queryset = get_all_users()
        role = self.request.query_params.get('role', None)
        if role:
            queryset = queryset.filter(role=role)
        return queryset
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'users': serializer.data,
            'count': queryset.count()
        })