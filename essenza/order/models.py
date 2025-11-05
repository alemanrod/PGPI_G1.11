from django.db import models

# Create your models here.
class Status(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PAID = 'paid', 'Paid'
    SHIPPED = 'shipped', 'Shipped'

class Order(models.Model):
    user = models.ForeignKey('user.Usuario', on_delete=models.CASCADE, related_name='orders')
    adress = models.CharField(max_length=255)
    placed_at = models.DateTimeField(auto_now=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    def __str__(self):
        return f"Order {self.id} by {self.user.email}"


class OrderProduct(models.Model):
    order = models.ForeignKey('order.Order', on_delete=models.CASCADE, related_name='order_products')
    product = models.ForeignKey('product.Product', on_delete=models.CASCADE, related_name='product_orders')
    quantity = models.IntegerField()
    unity_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} of {self.product.name} in order {self.order.id}"
