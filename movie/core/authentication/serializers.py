# users/serializers.py
from rest_framework import serializers
from users.models import CustomUser as User
from core.base.choices import RoleChoices
from authentication.validators import validate_password, validate_login

class RegisterSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField()
    username = serializers.CharField(required=True, max_length=150)
    password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=8,
        style={"input_type": "password"}
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=8,
        style={"input_type": "password"}
    )

    def create(self, validated_data):
        email = validated_data["email"]
        username = validated_data["username"]
        password = validated_data["password"]
        default_role = "user"  

        user = User.objects.create(
            email=email,
            username=username,
            role=default_role
        )
        user.set_password(password)
        user.save()
        return user

    def validate(self, attrs):
        if attrs.get('password') != attrs.get('confirm_password'):
            raise serializers.ValidationError({"password": "Passwords must match."})
        return validate_password(attrs)



class LoginSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField()
    password = serializers.CharField(
        style={"input_type": "password"}, trim_whitespace=False, write_only=True
    )

    def validate(self, attrs):
      return validate_login(attrs)
    
class ChangePasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"]
        password = attrs["old_password"]

        user = User.objects.filter(email=email).first()

        if not user:
            raise serializers.ValidationError("Invalid email.")

        if not user.check_password(password):
            flag = user.check_password(password)
            print("Check password failed ==========> ", flag)
            raise serializers.ValidationError("Invalid password.")

        new_password = attrs["new_password"]
        confirm_password = attrs["confirm_password"]

        if new_password != confirm_password:
            raise serializers.ValidationError(
                {"password": "Passwords must match."}
            )
        user.set_password(new_password)
        user.save()

        return attrs
    
class ForgotPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        password = attrs["password"]
        confirm_password = attrs["confirm_password"]

        if password != confirm_password:
            raise serializers.ValidationError(
                {"password": "Passwords must match."}
            )

        return attrs