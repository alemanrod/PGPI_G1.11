from django.db import models

# Create your models here.
class Role(models.TextChoices):
    ADMIN = 'admin', 'Admin'
    USER = 'user', 'User'


class Usuario(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True)
    foto = models.URLField(blank=True, null=True)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER)

    def __str__(self):
        return self.email

# user1@example.com, user
# user2@example.com, user
# admin1@example.com, admin