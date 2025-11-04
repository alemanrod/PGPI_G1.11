from django.db import models

# Create your models here.
class Status(models.TextChoices):
    OPEN = 'open', 'Open'
    PURCHASED = 'purchased', 'Purchased'
    ABANDONED = 'abandoned', 'Abandoned'

class Cart(models.Model):
    user = models.ForeignKey('user.Usuario', on_delete=models.CASCADE, related_name='carts')
    placed_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart {self.id} by {self.user.email}"

class CartProduct(models.Model):
    cart = models.ForeignKey('cart.Cart', on_delete=models.CASCADE, related_name='products_cart')
    product = models.ForeignKey('product.Product', on_delete=models.CASCADE, related_name='cart_products')
    quantity = models.IntegerField()
    unity_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self): 
        return f"{self.cart.id} - {self.product.name}"
