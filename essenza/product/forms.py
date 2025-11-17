from django import forms

from .models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "description",
            "category",
            "brand",
            "price",
            "photo",
            "stock",
            "is_active",
        ]
