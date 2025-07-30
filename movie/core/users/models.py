from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from users.managers import CustomUserManager
from core.base.models import BaseModel
from core.base.choices import RoleChoices


class UserStatusChoices(models.TextChoices):
    ACTIVE = 'active', 'Active'
    INACTIVE = 'inactive', 'Inactive'
    SUSPENDED = 'suspended', 'Suspended'


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
    
    def with_deleted(self):
        return super().get_queryset()
    
    def deleted_only(self):
        return super().get_queryset().filter(is_deleted=True)

class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()

    def soft_delete(self):
        """Soft delete the instance"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.is_active = False
        self.status = UserStatusChoices.INACTIVE
        self.save()

    def restore(self):
        """Restore a soft-deleted instance"""
        self.is_deleted = False
        self.deleted_at = None
        self.is_active = True
        self.status = UserStatusChoices.ACTIVE
        self.save()

    class Meta:
        abstract = True

class CustomUser(AbstractBaseUser, PermissionsMixin, BaseModel, SoftDeleteModel):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)

    # Role: viewer or admin only
    role = models.CharField(
        choices=RoleChoices.choices,
        default=RoleChoices.USER,
        max_length=20
    )

    status = models.CharField(
        choices=UserStatusChoices.choices,
        default=UserStatusChoices.ACTIVE,
        max_length=20
    )
    # Preferences and activity (extendable)
    # favorite_genres = models.JSONField(default=list, blank=True)
    # liked_movies = models.ManyToManyField(
    #     "movies.Movie", 
    #     blank=True, 
    #     related_name="liked_by"
    # )
    # watchlist = models.ManyToManyField(
    #     "movies.Watchlist", 
    #     blank=True, 
    #     related_name="watchlisted_by"
    # )

    # System fields
    date_joined = models.DateTimeField(default=timezone.now)
    # is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(blank=True, null=True)

    is_staff = models.BooleanField(default=False)  # set True only for admins

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return f"{self.username} ({self.email})"

    @property
    def is_admin(self):
        return self.role == RoleChoices.ADMIN

    def delete(self, *args, **kwargs):
        """Override default delete to use soft delete"""
        self.soft_delete()
    
    def hard_delete(self, *args, **kwargs):
        """Actual database deletion"""
        super().delete(*args, **kwargs)