from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from .forms import ProductForm
from .models import Product


class BaseView(View):
    def get(self, request):
        return render(request, "base.html")


class DashboardView(UserPassesTestMixin, View):
    template_name = "product/dashboard.html"

    # Todos excepto los administradores pueden acceder a esta vista
    def test_func(self):
        return (
            not self.request.user.is_authenticated or self.request.user.role != "admin"
        )

    def handle_no_permission(self):
        return redirect("stock")

    def get(self, request, *args, **kwargs):
        q = request.GET.get("q", "").strip()

        month_ago = timezone.now() - timezone.timedelta(days=30)
        year_ago = timezone.now() - timezone.timedelta(days=365)

        def get_top_selling_products(since):
            # Paso 1: Definir el filtro base.
            base_query = Product.objects.filter(
                is_active=True, product_orders__order__placed_at__gte=since
            )
            # Paso 2: Anotar (calcular) el total vendido para esos productos.
            query_with_totals = base_query.annotate(
                total_quantity=Sum("product_orders__quantity")
            )
            # Paso 3: Filtrar de nuevo, sobre el campo calculado.
            filtered_query = query_with_totals.filter(total_quantity__gt=0)
            # Paso 4: Ordenar (descendente).
            ordered_query = filtered_query.order_by("-total_quantity")
            top_products = ordered_query[:10]
            return top_products

        # If a search query is provided, show matching products instead of top sellers
        if q:
            products = Product.objects.filter(is_active=True, name__icontains=q)
            return render(
                request, self.template_name, {"products": products, "query": q}
            )

        products = get_top_selling_products(since=month_ago)
        if not products.exists():
            products = get_top_selling_products(since=year_ago)
        if not products.exists():
            products = Product.objects.filter(is_active=True).order_by("-stock")[:10]

        return render(request, self.template_name, {"products": products})


class StockView(LoginRequiredMixin, UserPassesTestMixin, View):
    # Solo los administradores pueden acceder a esta vista
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == "admin"

    # Redirige a 'dashboard' si no pasa el test_func
    def handle_no_permission(self):
        return redirect("dashboard")

    def get(self, request):
        # Carga y muestra todos los productos ordenados por nombre
        q = request.GET.get("q", "").strip()
        if q:
            products = Product.objects.filter(name__icontains=q).order_by("name")
        else:
            products = Product.objects.all().order_by("name")
        return render(request, "product/stock.html", {"products": products, "query": q})

    def post(self, request):
        # Coge datos del formulario para actualizar stock
        product_id = request.POST.get("product_id")
        stock_value = request.POST.get("stock")  # Renombrado para claridad

        product = get_object_or_404(Product, pk=product_id)

        try:
            # Comprobamos si el valor es un número
            new_stock = int(stock_value or 0)
            if new_stock < 0:
                # No permitir stock negativo
                raise ValueError("El stock no puede ser negativo")

            product.stock = new_stock
            product.save(update_fields=["stock"])

        except (ValueError, TypeError):
            pass

        # Recarga la misma página
        return redirect("stock")


class ProductListView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = "product/list.html"

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == "admin"

    def get(self, request):
        q = request.GET.get("q", "").strip()
        if q:
            products = Product.objects.filter(name__icontains=q)
        else:
            products = Product.objects.all()
        return render(request, self.template_name, {"products": products, "query": q})


class ProductDetailView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = "product/detail.html"

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == "admin"

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        return render(request, self.template_name, {"product": product})


class ProductCreateView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = "product/create_product.html"
    form_class = ProductForm

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == "admin"

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = self.form_class(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("product_list")
        return render(request, self.template_name, {"form": form})


class ProductUpdateView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = "product/update_product.html"
    form_class = ProductForm

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == "admin"

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        form = self.form_class(instance=product)
        return render(request, self.template_name, {"form": form, "product": product})

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        form = self.form_class(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect("product_list")
        return render(request, self.template_name, {"form": form, "product": product})


class ProductDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = "product/confirm_delete.html"

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == "admin"

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        return render(request, self.template_name, {"product": product})

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.delete()
        return redirect("product_list")


class CatalogView(View):
    template_name = "product/catalog.html"

    def get(self, request):
        q = request.GET.get("q", "").strip()
        if q:
            products = Product.objects.filter(is_active=True, name__icontains=q)
        else:
            products = Product.objects.filter(is_active=True)
        return render(request, self.template_name, {"products": products, "query": q})


class CatalogDetailView(View):
    template_name = "product/detail_user.html"

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk, is_active=True)
        return render(request, self.template_name, {"product": product})
