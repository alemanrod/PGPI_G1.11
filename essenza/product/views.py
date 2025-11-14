from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from .forms import ProductForm
from order.models import OrderProduct
from .models import Product

class DashboardView(View):
    template_name = "product/dashboard.html"

    def get(self, request, *args, **kwargs):
        # Obtenemos de los datos
        order_products = OrderProduct.objects.all()
        month_ago = timezone.now() - timezone.timedelta(days=30)
        times_purchased = {}
        for order_product in order_products:
            order = order_product.order
            if order.placed_at >= month_ago:
                if order_product.product.id in times_purchased:
                    times_purchased[order_product.product.id] += order_product.quantity
                else:
                    times_purchased[order_product.product.id] = order_product.quantity
        times_purchased_ordered = dict(
            sorted(
                times_purchased.items(), key=lambda quantity: quantity[1], reverse=True
            )
        )
        most_purchased_products = list(times_purchased_ordered.keys())[:10]
        products = Product.objects.filter(
            is_active=True, id__in=most_purchased_products
        )

        return render(request, self.template_name, {"products": products})


class StockView(LoginRequiredMixin, UserPassesTestMixin, View):
    # Solo los administradores pueden acceder a esta vista
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == "admin"

    # Solo se ejecutan métodos GET y POST si el usuario pasa la prueba
    def get(self, request):
        # Carga y muestra todos los productos ordenados por nombre
        products = Product.objects.all().order_by("name")
        return render(request, "product/stock.html", {"products": products})

    def post(self, request):
        # Coge datos del formulario para actualizar stock
        product_id = request.POST.get("product_id")
        stock = request.POST.get("stock")

        # Encuentra el producto por su ID
        product = Product.objects.get(pk=product_id)
        if not product:
            messages.error(request, "Producto no encontrado.")
            return redirect("stock")

        # Actualiza el stock del producto
        new_stock = int(stock or 0)
        product.stock = new_stock
        product.save(update_fields=["stock"])
        messages.success(
            request, f"Stock de '{product.name}' actualizado a {new_stock}."
        )

        # Recarga la misma página
        return redirect("stock")
    

class ProductListView(View):
    template_name = 'product/list.html'

    def get(self, request):
        products = Product.objects.all()
        return render(request, self.template_name, {'products': products})

class ProductDetailView(View):
    template_name = 'product/detail.html'


    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        return render(request, self.template_name, {'product': product})
    
class ProductCreateView(View):
    template_name = 'product/form.html'
    form_class = ProductForm
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == "admin"

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = self.form_class(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('product_list')
        return render(request, self.template_name, {'form': form})

class ProductUpdateView(View):
    template_name = 'product/form.html'
    form_class = ProductForm
    
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == "admin"
   
    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        form = self.form_class(instance=product)
        return render(request, self.template_name, {'form': form, 'product': product})


    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        form = self.form_class(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('product_detail', pk=product.pk)
        return render(request, self.template_name, {'form': form, 'product': product})

class ProductDeleteView(View):
    template_name = 'product/confirm_delete.html'

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == "admin"
    
    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        return render(request, self.template_name, {'product': product})


    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.delete()
        return redirect('product_list')
