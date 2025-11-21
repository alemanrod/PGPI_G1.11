from django.db import models


class Cart(models.Model):
    user = models.ForeignKey(
        "user.Usuario", on_delete=models.CASCADE, related_name="cart"
    )

    @property
    def total_price(self):
        total = 0
        for product in self.cart_products.all():
            total += product.subtotal
        return total

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
