from django.contrib.auth.models import BaseUserManager
from core.base.choices import RoleChoices

class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field is required.")
        if not username:
            raise ValueError("The Username field is required.")

        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('role', RoleChoices.ADMIN)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('role') != RoleChoices.ADMIN:
            raise ValueError("Superuser must have role='admin'.")
        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, username, password, **extra_fields)
    
    def with_deleted(self):
        return super().get_queryset()
    
    def deleted_only(self):
        return super().get_queryset().filter(is_deleted=True)
