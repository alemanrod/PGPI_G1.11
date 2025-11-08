from django.db import models
from django.contrib.auth.models import AbstractUser

class Role(models.TextChoices):
    ADMIN = 'admin', 'Admin'
    USER = 'user', 'User'

class Usuario(AbstractUser):
    foto = models.ImageField(upload_to='images/', null=True, blank=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER)

    email = models.EmailField(unique=True) 

    USERNAME_FIELD = 'email'               
    REQUIRED_FIELDS = ['username']     

    def __str__(self):
        return self.email