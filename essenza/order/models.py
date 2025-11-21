import random
import string

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone


# Create your models here.
class Status(models.TextChoices):
    EN_PREPARACION = "en_preparacion", "En Preparación"
    ENVIADO = "enviado", "Enviado"
    ENTREGADO = "entregado", "Entregado"


class Order(models.Model):
    user = models.ForeignKey(
        "user.Usuario",
        on_delete=models.SET_NULL,
        related_name="orders",
        null=True,
        blank=True,
    )
    email = models.EmailField(max_length=254, null=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    placed_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(choices=Status.choices, default=Status.EN_PREPARACION)

    tracking_code = models.CharField(
        max_length=4,
        unique=True,
        editable=False,  # No se puede editar manualmente
        verbose_name="Localizador",
    )

    @property
    def total_price(self):
        total = 0
        for product in self.order_products.all():
            total += product.subtotal
        return total

    def save(self, *args, **kwargs):
        """
        Sobrescribimos el método save para generar el tracking_code
        automáticamente antes de guardar si aún no tiene uno.
        """

        if not self.tracking_code:
            self.tracking_code = self._generate_unique_tracking_code()

        if not self.user and self.email:
            User = get_user_model()
            # Buscamos si existe algún usuario registrado con ese correo
            existing_user = User.objects.filter(email=self.email).first()

            if existing_user:
                self.user = existing_user
        super().save(*args, **kwargs)

    def _generate_unique_tracking_code(self):
        """Genera un código único de 4 dígitos numéricos."""
        while True:
            code = "".join(random.choices(string.digits, k=4))
            # Verifica que no exista para evitar duplicados
            if not Order.objects.filter(tracking_code=code).exists():
                return code

    def __str__(self):
        return f"Order {self.id} [{self.tracking_code}] - {self.email}"


class OrderProduct(models.Model):
    order = models.ForeignKey(
        "order.Order", on_delete=models.CASCADE, related_name="order_products"
    )
    product = models.ForeignKey(
        "product.Product", on_delete=models.CASCADE, related_name="product_orders"
    )
    quantity = models.IntegerField()

    @property
    def subtotal(self):
        return self.quantity * self.product.price

    def __str__(self):
        return f"{self.quantity} of {self.product.name} in order {self.order.tracking_code}"
