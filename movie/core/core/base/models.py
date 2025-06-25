import uuid

from django.db import models
from core.base.choices import GenderChoices

class BaseModel(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class Profile(BaseModel):
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(choices=GenderChoices, blank=True)

    class Meta:
        abstract = True
