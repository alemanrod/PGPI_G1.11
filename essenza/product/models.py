from django.db import models

# Create your models here.
class Category(models.TextChoices):
    MAQUILLAJE = 'maquillaje', 'Maquillaje'
    TRATAMIENTO = 'tratamiento', 'Tratamiento'
    CABELLO = 'cabello', 'Cabello'
    PERFUME = 'perfume', 'Perfume'

class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    categoria = models.CharField(max_length=20, choices=Category.choices)
    brand = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

