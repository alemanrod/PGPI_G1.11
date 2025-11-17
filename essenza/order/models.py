from django.db import models
from django.utils import timezone


# Create your models here.
class Status(models.TextChoices):
    PENDING = "pending", "Pending"
    PAID = "paid", "Paid"
    SHIPPED = "shipped", "Shipped"


class Order(models.Model):
    user = models.ForeignKey(
        "user.Usuario", on_delete=models.CASCADE, related_name="orders"
    )
    address = models.CharField(max_length=255)
    placed_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )

    @property
    def total_price(self):
        total = 0
        for product in self.order_products.all():
            total += product.quantity * product.product.price
        return total

    def __str__(self):
        return f"Order {self.id} by {self.user.email}"


class OrderProduct(models.Model):
    order = models.ForeignKey(
        "order.Order", on_delete=models.CASCADE, related_name="order_products"
    )
    product = models.ForeignKey(
        "product.Product", on_delete=models.CASCADE, related_name="product_orders"
    )
    quantity = models.IntegerField()

    def __str__(self):
        return f"{self.quantity} of {self.product.name} in order {self.order.id}"
