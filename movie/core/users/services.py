# apps/users/services.py

from users.models import CustomUser
from django.utils import timezone
from typing import Optional

def create_user(email: str, username: str, password: str, **extra_fields) -> CustomUser:
    user = CustomUser.objects.create_user(
        email=email,
        username=username,
        password=password,
        **extra_fields
    )
    return user

def update_user_profile(user: CustomUser, data: dict) -> CustomUser:
    for attr, value in data.items():
        setattr(user, attr, value)
    user.save()
    return user

def deactivate_user(user: CustomUser) -> CustomUser:
    user.is_active = False
    user.save()
    return user
