from django.contrib import admin
from .models import Cart, CartProduct, Status

# Register your models here.
admin.site.register(Cart)
admin.site.register(CartProduct)
