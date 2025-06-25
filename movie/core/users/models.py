from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from users.managers import CustomUserManager
from core.base.models import BaseModel
from core.base.choices import RoleChoices

class CustomUser(AbstractBaseUser, PermissionsMixin, BaseModel):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)

    # Role: viewer or admin only
    role = models.CharField(
        choices=RoleChoices.choices,
        default=RoleChoices.USER,
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
    #     "movies.Movie", 
    #     blank=True, 
    #     related_name="watchlisted_by"
    # )

    # System fields
    date_joined = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # set True only for admins

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return f"{self.username} ({self.email})"

    @property
    def is_admin(self):
        return self.role == RoleChoices.ADMIN
