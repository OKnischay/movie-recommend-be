from rest_framework import serializers
from users.models import CustomUser as User

def validate_login(attrs):
    email = attrs.get("email")
    password = attrs.get("password")

    user = User.objects.filter(email=email).first()

    # if not user:
    #         raise serializers.ValidationError("Invalid crendentials.")

    if not user or getattr(user, 'is_deleted', False):
        raise serializers.ValidationError("Invalid credentials")
    
    if not user.check_password(password):
            raise serializers.ValidationError("Invalid password.")
    
    if not user.is_active:
        raise serializers.ValidationError("Account is inactive")

    attrs["user"] = user
    return attrs

def validate_password(attrs):
    password = attrs.get("password")
    confirm_password = attrs.get("confirm_password")

    if password != confirm_password:
        raise serializers.ValidationError({"message": "Passwords do not match."})
    
    # validate_password(password) 
    return attrs