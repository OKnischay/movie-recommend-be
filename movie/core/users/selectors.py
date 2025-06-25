# apps/users/selectors.py

from users.models import CustomUser
from django.db.models import QuerySet
from typing import Optional

def get_user_by_email(email: str) -> Optional[CustomUser]:
    return CustomUser.objects.filter(email=email).first()

def get_user_by_id(user_id: str) -> Optional[CustomUser]:
    return CustomUser.objects.filter(id=user_id).first()

def get_all_users() -> QuerySet[CustomUser]:
    return CustomUser.objects.all()

def get_admin_users() -> QuerySet[CustomUser]:
    return CustomUser.objects.filter(role="admin")

def get_viewers() -> QuerySet[CustomUser]:
    return CustomUser.objects.filter(role="viewer")
