from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from order.models import Order, OrderProduct

from .models import Category, Product

User = get_user_model()


class DashboardViewLogicTests(TestCase):
    def setUp(self):
        self.dashboard_url = reverse("dashboard")
        self.login_url = reverse("login")
        self.now = timezone.now()

        # --- Usuarios (Usando tus roles 'admin' y 'user') ---
        self.admin_user = User.objects.create_user(
            username="admin", email="admin@test.com", password="pass", role="admin"
        )
        self.regular_user = User.objects.create_user(
            username="user", email="user@test.com", password="pass", role="user"
        )

        # --- Productos ---
        self.p_30_day = Product.objects.create(
            name="Producto 30 Días",
            description="Test Desc",
            category=Category.MAQUILLAJE,
            brand="TestBrand",
            price=10.00,
            stock=10,
            is_active=True,
        )
        self.p_1_year = Product.objects.create(
            name="Producto 1 Año",
            description="Test Desc",
            category=Category.CABELLO,
            brand="TestBrand",
            price=20.00,
            stock=20,
            is_active=True,
        )
        self.p_stock = Product.objects.create(
            name="Producto Stock Alto",
            description="Test Desc",
            category=Category.PERFUME,
            brand="TestBrand",
            price=30.00,
            stock=999,
            is_active=True,
        )
        self.p_stock_low = Product.objects.create(
            name="Producto Stock Bajo",
            description="Test Desc",
            category=Category.TRATAMIENTO,
            brand="TestBrand",
            price=40.00,
            stock=1,
            is_active=True,
        )
        self.p_inactive = Product.objects.create(
            name="Producto Inactivo",
            description="Test Desc",
            category=Category.MAQUILLAJE,
            brand="TestBrand",
            price=50.00,
            stock=1000,
            is_active=False,
        )

    # --- 1. Tests de Permisos (test_func) ---

    def test_anonymous_user_gets_200(self):
        """Prueba que los anónimos pueden ver la vista."""
        resp = self.client.get(self.dashboard_url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "product/dashboard.html")

    def test_regular_user_gets_200(self):
        """Prueba que los usuarios 'user' pueden ver la vista."""
        self.client.login(email="user@test.com", password="pass")
        resp = self.client.get(self.dashboard_url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "product/dashboard.html")

    def test_admin_user_is_forbidden(self):
        """Prueba que los 'admin' son bloqueados."""
        self.client.login(email="admin@test.com", password="pass")
        resp = self.client.get(self.dashboard_url)
        self.assertEqual(resp.status_code, 403)

    # --- 2. Tests de Lógica de Negocio (método get) ---

    def test_logic_branch_1_shows_30_day_products(self):
        """
        Prueba el primer 'if': Muestra productos de 30 días.
        Ignora ventas más antiguas aunque sean mayores.
        """
        # 1. Crear ventas recientes (hace 10 días)
        order_recent = Order.objects.create(
            user=self.regular_user,
            address="Test Address 1",
            placed_at=self.now
            - timezone.timedelta(days=10),  # <-- Controlamos la fecha
        )
        OrderProduct.objects.create(
            order=order_recent, product=self.p_30_day, quantity=100
        )

        # 2. Crear ventas antiguas (hace 100 días)
        order_old = Order.objects.create(
            user=self.regular_user,
            address="Test Address 2",
            placed_at=self.now - timezone.timedelta(days=100),
        )
        OrderProduct.objects.create(
            order=order_old,
            product=self.p_1_year,
            quantity=500,  # Más ventas, pero antiguo
        )

        resp = self.client.get(self.dashboard_url)
        products_in_context = list(resp.context["products"])

        # ASERCIÓN: Solo debe aparecer el producto de 30 días
        self.assertEqual(len(products_in_context), 1)
        self.assertEqual(products_in_context[0], self.p_30_day)
        self.assertEqual(products_in_context[0].total_quantity, 100)

    def test_logic_branch_2_falls_back_to_1_year_products(self):
        """
        Prueba el segundo 'if': Falla 30 días, muestra 1 año.
        Ignora ventas de hace más de 1 año.
        """
        # 1. NO crear ventas recientes

        # 2. Crear ventas antiguas (hace 100 días)
        order_old = Order.objects.create(
            user=self.regular_user,
            address="Test Address 1",
            placed_at=self.now - timezone.timedelta(days=100),
        )
        OrderProduct.objects.create(
            order=order_old, product=self.p_1_year, quantity=500
        )

        # 3. Crear ventas MUY antiguas (hace 400 días) - debe ignorarse
        order_ancient = Order.objects.create(
            user=self.regular_user,
            address="Test Address 2",
            placed_at=self.now - timezone.timedelta(days=400),
        )
        OrderProduct.objects.create(
            order=order_ancient, product=self.p_30_day, quantity=999
        )

        resp = self.client.get(self.dashboard_url)
        products_in_context = list(resp.context["products"])

        # ASERCIÓN: Solo debe aparecer el producto de 1 año
        self.assertEqual(len(products_in_context), 1)
        self.assertEqual(products_in_context[0], self.p_1_year)
        self.assertEqual(products_in_context[0].total_quantity, 500)

    def test_logic_branch_3_falls_back_to_stock_products(self):
        """
        Prueba el tercer 'if': Falla 1 año, muestra por stock.
        Ignora ventas de productos inactivos.
        """
        # 1. NO crear ventas recientes
        # 2. NO crear ventas en el último año

        # 3. Crear ventas MUY antiguas (hace 400 días) - para forzar el fallback
        order_ancient = Order.objects.create(
            user=self.regular_user,
            address="Test Address 1",
            placed_at=self.now - timezone.timedelta(days=400),
        )
        OrderProduct.objects.create(
            order=order_ancient, product=self.p_30_day, quantity=999
        )

        # 4. Crear ventas de productos INACTIVOS (deben ignorarse siempre)
        order_inactive = Order.objects.create(
            user=self.regular_user,
            address="Test Address 2",
            placed_at=self.now - timezone.timedelta(days=10),  # Reciente, pero inactivo
        )
        OrderProduct.objects.create(
            order=order_inactive, product=self.p_inactive, quantity=5000
        )

        resp = self.client.get(self.dashboard_url)
        products_in_context = list(resp.context["products"])

        # ASERCIÓN: Debe mostrar los productos activos por stock descendente
        # p_stock (999) > p_1_year (20) > p_30_day (10) > p_stock_low (1)
        # p_inactive (1000) debe ser ignorado.

        self.assertIn(self.p_stock, products_in_context)
        self.assertIn(self.p_1_year, products_in_context)
        self.assertNotIn(self.p_inactive, products_in_context)  # Clave

        # Comprobar el orden por stock
        self.assertEqual(products_in_context[0], self.p_stock)  # stock 999
        self.assertEqual(products_in_context[1], self.p_1_year)  # stock 20
        self.assertEqual(products_in_context[2], self.p_30_day)  # stock 10
        self.assertEqual(products_in_context[3], self.p_stock_low)  # stock 1

        # Comprobar que no hay 'total_quantity' (viene de la consulta de stock)
        self.assertFalse(hasattr(products_in_context[0], "total_quantity"))

    def test_logic_branch_4_handles_empty_database(self):
        """
        Prueba el caso límite final: No hay productos activos en la BBDD.
        La vista debe devolver una lista vacía, no romperse.
        """

        # 1. Borrar TODOS los productos creados en el setUp
        #    (Esto deja la BBDD sin productos activos)
        Product.objects.all().delete()

        # Cargar la vista
        resp = self.client.get(self.dashboard_url)
        self.assertEqual(resp.status_code, 200)

        # ASERCIÓN:
        # El contexto 'products' debe existir, pero estar vacío.
        self.assertIn("products", resp.context)
        products_in_context = list(resp.context["products"])

        self.assertEqual(len(products_in_context), 0)
