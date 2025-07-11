from rest_framework import serializers
from users.models import CustomUser

class UserSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CustomUser
        fields = ["id", "email", "username", "role","date_joined"]

class UserStatusSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'role', 'is_active', 'status', 'date_joined']
        
    def get_status(self, obj):
        # Convert boolean is_active to string for frontend compatibility
        return 'active' if obj.is_active else 'inactive'
        
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Format date_joined
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


