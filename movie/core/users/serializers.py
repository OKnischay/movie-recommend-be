from rest_framework import serializers
from users.models import CustomUser

class UserSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CustomUser
        fields = ["id", "email", "username", "role","date_joined"]

class UserStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'role',
            'is_active', 'status', 'is_deleted', 'date_joined'
        ]
        
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation['date_joined']:
            representation['date_joined'] = instance.date_joined.strftime('%Y-%m-%d')
        return representation


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = "__all__"

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["email", "username"]


