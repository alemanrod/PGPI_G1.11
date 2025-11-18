from django import forms

from .models import Product


class ProductForm(forms.ModelForm):
    photo = forms.ImageField(
        label="Foto (Opcional)", required=False, widget=forms.FileInput
    )
    remove_photo = forms.BooleanField(required=False, label="Eliminar foto actual")
    stock = forms.IntegerField(label="Cantidad en stock", min_value=0, required=False)
    is_active = forms.BooleanField(
        required=False, label="Producto activo", initial=True
    )
    description = forms.CharField(
        label="Descripción", widget=forms.Textarea(attrs={"rows": 4})
    )

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
