from decimal import Decimal

from django.db import models


class Cart(models.Model):
    user = models.ForeignKey(
        "user.Usuario", on_delete=models.CASCADE, related_name="cart"
    )

    @property
    def shipping(self):
        return Decimal(4.99 if self.subtotal < 100 else 0)

    @property
    def subtotal(self):
        subtotal = 0
        for product in self.cart_products.all():
            subtotal += product.subtotal
        return Decimal(subtotal)

    @property
    def total(self):
        return self.subtotal + self.shipping

    def __str__(self):
        return f"Cart {self.id} by {self.user.email}"


class CartProduct(models.Model):
    cart = models.ForeignKey(
        "cart.Cart", on_delete=models.CASCADE, related_name="cart_products"
    )
    product = models.ForeignKey(
        "product.Product", on_delete=models.CASCADE, related_name="product_carts"
    )
    quantity = models.IntegerField()

    @property
    def subtotal(self):
        return self.quantity * self.product.price

    def __str__(self):
        return f"{self.quantity} of {self.product.name} in cart {self.cart.id}"
