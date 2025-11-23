from django.db import models


# Create your models here.
class Category(models.TextChoices):
    MAQUILLAJE = "maquillaje", "Maquillaje"
    TRATAMIENTO = "tratamiento", "Tratamiento"
    CABELLO = "cabello", "Cabello"
    PERFUME = "perfume", "Perfume"
    SERVICIO = "servicio", "Servicio"


class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=Category.choices)
    brand = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    photo = models.ImageField(upload_to="products/", null=True, blank=True)
    stock = models.IntegerField(default=0)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.name
