from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from order.models import Order, OrderProduct

from .models import Product

User = get_user_model()


class DashboardViewTests(TestCase):
    def setUp(self):
        self.dashboard_url = reverse("dashboard")
        self.login_url = reverse("login")
        self.now = timezone.now()

        # --- Usuarios ---
        self.admin_user = User.objects.create_user(
            username="admin", email="admin@test.com", password="pass", role="admin"
        )
        self.regular_user = User.objects.create_user(
            username="user", email="user@test.com", password="pass", role="customer"
        )

        # --- Productos Base ---
        # Estos se usarán para crear órdenes
        self.p_30_day = Product.objects.create(
            name="Producto 30 Días", is_active=True, stock=10
        )
        self.p_1_year = Product.objects.create(
            name="Producto 1 Año", is_active=True, stock=20
        )
        self.p_stock = Product.objects.create(
            name="Producto Stock Alto", is_active=True, stock=999
        )
        self.p_stock_low = Product.objects.create(
            name="Producto Stock Bajo", is_active=True, stock=1
        )
        self.p_inactive = Product.objects.create(
            name="Producto Inactivo", is_active=False, stock=1000
        )

    # --- 1. Tests de Permisos (test_func) ---

    def test_anonymous_user_gets_200(self):
        """Los usuarios anónimos pueden ver la vista."""
        resp = self.client.get(self.dashboard_url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "product/dashboard.html")

    def test_regular_user_gets_200(self):
        """Los usuarios logueados (no admin) pueden ver la vista."""
        self.client.login(email="user@test.com", password="pass")
        resp = self.client.get(self.dashboard_url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "product/dashboard.html")

    def test_admin_user_is_redirected(self):
        """Los admins fallan el test_func y son redirigidos."""
        self.client.login(email="admin@test.com", password="pass")
        resp = self.client.get(self.dashboard_url)
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, f"{self.login_url}?next={self.dashboard_url}")

    # --- 2. Tests de Lógica de Negocio (método get) ---

    def test_logic_branch_1_shows_30_day_products(self):
        """Prueba el primer 'if': Muestra productos de 30 días."""

        # 1. Crear ventas recientes (hace 10 días)
        order_recent = Order.objects.create(
            user=self.regular_user, placed_at=self.now - timezone.timedelta(days=10)
        )
        OrderProduct.objects.create(
            order=order_recent, product=self.p_30_day, quantity=100
        )

        # 2. Crear ventas antiguas (hace 100 días)
        order_old = Order.objects.create(
            user=self.regular_user, placed_at=self.now - timezone.timedelta(days=100)
        )
        OrderProduct.objects.create(
            order=order_old,
            product=self.p_1_year,
            quantity=500,  # Más vendido, pero antiguo
        )

        # (El 'p_stock' no tiene ventas, solo stock alto)

        # Cargar la vista
        resp = self.client.get(self.dashboard_url)
        self.assertEqual(resp.status_code, 200)
        products_in_context = list(resp.context["products"])

        # ASERCIÓN:
        # El producto de 30 días debe ser el primero y único
        self.assertEqual(len(products_in_context), 1)
        self.assertEqual(products_in_context[0], self.p_30_day)
        self.assertEqual(products_in_context[0].total_quantity, 100)

    def test_logic_branch_2_falls_back_to_1_year_products(self):
        """Prueba el segundo 'if': Falla 30 días, muestra 1 año."""

        # 1. NO crear ventas recientes

        # 2. Crear ventas antiguas (hace 100 días)
        order_old = Order.objects.create(
            user=self.regular_user, placed_at=self.now - timezone.timedelta(days=100)
        )
        OrderProduct.objects.create(
            order=order_old, product=self.p_1_year, quantity=500
        )

        # 3. Crear ventas MUY antiguas (hace 400 días) - deben ignorarse
        order_ancient = Order.objects.create(
            user=self.regular_user, placed_at=self.now - timezone.timedelta(days=400)
        )
        OrderProduct.objects.create(
            order=order_ancient, product=self.p_30_day, quantity=999
        )

        # Cargar la vista
        resp = self.client.get(self.dashboard_url)
        self.assertEqual(resp.status_code, 200)
        products_in_context = list(resp.context["products"])

        # ASERCIÓN:
        # El producto de 1 año debe ser el primero y único
        self.assertEqual(len(products_in_context), 1)
        self.assertEqual(products_in_context[0], self.p_1_year)
        self.assertEqual(products_in_context[0].total_quantity, 500)

    def test_logic_branch_3_falls_back_to_stock_products(self):
        """Prueba el tercer 'if': Falla 1 año, muestra por stock."""

        # 1. NO crear ventas recientes

        # 2. NO crear ventas en el último año

        # 3. Crear ventas MUY antiguas (hace 400 días) - para que fallen los dos 'if'
        order_ancient = Order.objects.create(
            user=self.regular_user, placed_at=self.now - timezone.timedelta(days=400)
        )
        OrderProduct.objects.create(
            order=order_ancient, product=self.p_30_day, quantity=999
        )

        # 4. Crear ventas de productos INACTIVOS (deben ignorarse siempre)
        order_inactive = Order.objects.create(
            user=self.regular_user, placed_at=self.now - timezone.timedelta(days=10)
        )
        OrderProduct.objects.create(
            order=order_inactive, product=self.p_inactive, quantity=5000
        )

        # Cargar la vista
        resp = self.client.get(self.dashboard_url)
        self.assertEqual(resp.status_code, 200)
        products_in_context = list(resp.context["products"])

        # ASERCIÓN:
        # Debe mostrar productos por stock descendente.
        # p_stock (999) > p_1_year (20) > p_30_day (10) > p_stock_low (1)
        # p_inactive (1000) debe ser ignorado.

        self.assertIn(self.p_stock, products_in_context)
        self.assertIn(self.p_1_year, products_in_context)
        self.assertNotIn(self.p_inactive, products_in_context)  # Importante

        # Comprobar el orden por stock
        self.assertEqual(products_in_context[0], self.p_stock)  # stock 999
        self.assertEqual(products_in_context[1], self.p_1_year)  # stock 20
        self.assertEqual(products_in_context[2], self.p_30_day)  # stock 10
        self.assertEqual(products_in_context[3], self.p_stock_low)  # stock 1

        # Comprobar que no hay 'total_quantity' (viene de otra consulta)
        self.assertFalse(hasattr(products_in_context[0], "total_quantity"))
