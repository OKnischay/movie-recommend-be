from django.db import models

class GenderChoices(models.TextChoices):
    Male = "Male"
    Female = "Female"
    Others = "Others"

class RoleChoices(models.TextChoices):
    USER = "user", "User"
    ADMIN = "admin", "Admin"
 
 