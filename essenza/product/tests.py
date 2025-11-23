from decimal import Decimal

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
        self.assertEqual(resp.status_code, 302)

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
        order_old = Order.objects.create(
            user=self.regular_user,
            address="Test Address 1",
            placed_at=self.now - timezone.timedelta(days=100),
        )
        OrderProduct.objects.create(
            order=order_old, product=self.p_1_year, quantity=500
        )

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

        self.assertEqual(len(products_in_context), 1)
        self.assertEqual(products_in_context[0], self.p_1_year)
        self.assertEqual(products_in_context[0].total_quantity, 500)

    def test_logic_branch_3_falls_back_to_stock_products(self):
        """
        Prueba el tercer 'if': Falla 1 año, muestra por stock.
        Ignora ventas de productos inactivos.
        """
        order_ancient = Order.objects.create(
            user=self.regular_user,
            address="Test Address 1",
            placed_at=self.now - timezone.timedelta(days=400),
        )
        OrderProduct.objects.create(
            order=order_ancient, product=self.p_30_day, quantity=999
        )

        order_inactive = Order.objects.create(
            user=self.regular_user,
            address="Test Address 2",
            placed_at=self.now - timezone.timedelta(days=10),  # Reciente, pero inactivo
            tracking_code="4957",
        )
        OrderProduct.objects.create(
            order=order_inactive, product=self.p_inactive, quantity=5000
        )

        resp = self.client.get(self.dashboard_url)
        products_in_context = list(resp.context["products"])

        self.assertIn(self.p_stock, products_in_context)
        self.assertIn(self.p_1_year, products_in_context)
        self.assertNotIn(self.p_inactive, products_in_context)  # Clave

        self.assertEqual(products_in_context[0], self.p_stock)  # stock 999
        self.assertEqual(products_in_context[1], self.p_1_year)  # stock 20
        self.assertEqual(products_in_context[2], self.p_30_day)  # stock 10
        self.assertEqual(products_in_context[3], self.p_stock_low)  # stock 1

        self.assertFalse(hasattr(products_in_context[0], "total_quantity"))

    def test_logic_branch_4_handles_empty_database(self):
        """
        Prueba el caso límite final: No hay productos activos en la BBDD.
        La vista debe devolver una lista vacía, no romperse.
        """

        Product.objects.all().delete()

        resp = self.client.get(self.dashboard_url)
        self.assertEqual(resp.status_code, 200)

        self.assertIn("products", resp.context)
        products_in_context = list(resp.context["products"])

        self.assertEqual(len(products_in_context), 0)


class ProductCRUDTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="user",
            email="user@example.com",
            password="pass1234",
            role="user",
        )
        # Crear usuario admin
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="pass1234",
            role="admin",
        )
        # Crear producto inicial
        self.product = Product.objects.create(
            name="Producto Test",
            description="Descripción",
            brand="Marca X",
            price=10,
            photo=None,
            stock=5,
            category="maquillaje",
            is_active=True,
        )
        # URLs
        self.list_url = reverse("product_list")
        self.detail_url = reverse("product_detail", args=[self.product.pk])
        self.create_url = reverse("product_create")
        self.update_url = reverse("product_update", args=[self.product.pk])
        self.delete_url = reverse("product_delete", args=[self.product.pk])

    # ---------------------------------------------------
    #   TESTS PARA USUARIO NO AUTENTICADO
    # ---------------------------------------------------

    def test_list_requires_login(self):
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.url)

    def test_detail_requires_login(self):
        resp = self.client.get(self.detail_url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.url)

    def test_create_requires_login(self):
        resp = self.client.get(self.create_url)
        self.assertEqual(resp.status_code, 302)

    # ---------------------------------------------------
    #   TESTS PARA USUARIO AUTENTICADO PERO NO ADMIN
    # ---------------------------------------------------

    def test_user_cannot_access_list(self):
        self.client.login(username="user", password="pass1234")
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, 302)  # Redirigido por permisos

    def test_user_cannot_access_detail(self):
        self.client.login(username="user", password="pass1234")
        resp = self.client.get(self.detail_url)
        self.assertEqual(resp.status_code, 302)

    def test_user_cannot_access_create(self):
        self.client.login(username="user", password="pass1234")
        resp = self.client.get(self.create_url)
        self.assertEqual(resp.status_code, 302)

    # ---------------------------------------------------
    #   TESTS PARA USUARIO ADMIN (PERMISO TOTAL)
    # ---------------------------------------------------

    def test_admin_can_access_list(self):
        self.client.force_login(self.admin)
        url = reverse("product_list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Producto Test")

    def test_admin_can_access_detail(self):
        self.client.force_login(self.admin)
        url = reverse("product_detail", args=[self.product.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.product.name)

    def test_admin_can_create_product(self):
        """Prueba que un admin puede crear un nuevo producto (POST)."""
        self.client.force_login(self.admin)

        initial_count = Product.objects.count()

        data = {
            "name": "Nuevo Producto Creado",
            "description": "Creado por el test de admin",
            "category": "perfume",
            "brand": "NewBrand",
            "price": "99.99",
            "stock": 100,
            "is_active": True,
        }
        resp = self.client.post(self.create_url, data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Product.objects.count(), initial_count + 1)
        self.assertTrue(Product.objects.filter(name="Nuevo Producto Creado").exists())

    def test_admin_can_update_product(self):
        """Prueba que un admin puede actualizar un producto existente (POST)."""
        self.client.force_login(self.admin)

        updated_name = "Nombre Actualizado Admin"
        updated_price = "15.50"

        data = {
            "name": updated_name,
            "description": "Descripción actualizada",
            "category": "tratamiento",
            "brand": self.product.brand,
            "price": updated_price,
            "stock": 50,
            "is_active": False,
        }
        resp = self.client.post(self.update_url, data)
        self.assertEqual(resp.status_code, 302)

        self.assertRedirects(resp, reverse("product_list"))

        self.product.refresh_from_db()
        self.assertEqual(self.product.name, updated_name)
        self.assertEqual(self.product.price, Decimal(updated_price))
        self.assertFalse(self.product.is_active)
        self.assertEqual(self.product.stock, 50)

    def test_admin_can_delete_product(self):
        self.client.force_login(self.admin)
        url = reverse("product_delete", args=[self.product.pk])

        # GET renderiza el confirm delete
        resp_get = self.client.get(url)
        self.assertEqual(resp_get.status_code, 200)

        # POST borra el producto
        resp_post = self.client.post(url)
        self.assertEqual(resp_post.status_code, 302)

        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())


class CatalogViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Producto visible en el catálogo (is_active = True)
        cls.active_product = Product.objects.create(
            name="Producto Activo",
            description="Descripción producto activo",
            category=Category.MAQUILLAJE,
            brand="Marca A",
            price=Decimal("19.99"),
            stock=10,
            is_active=True,
        )

        # Producto NO visible en el catálogo (is_active = False)
        cls.inactive_product = Product.objects.create(
            name="Producto Inactivo",
            description="Descripción producto inactivo",
            category=Category.TRATAMIENTO,
            brand="Marca B",
            price=Decimal("9.99"),
            stock=5,
            is_active=False,
        )

    def test_catalog_url_status_code(self):
        """La URL del catálogo responde con 200."""
        url = reverse("catalog")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_catalog_uses_correct_template(self):
        """El catálogo usa la plantilla correcta."""
        url = reverse("catalog")
        response = self.client.get(url)
        self.assertTemplateUsed(response, "product/catalog.html")

    def test_catalog_shows_only_active_products(self):
        """
        En el catálogo solo aparecen productos activos
        (is_active=True).
        """
        url = reverse("catalog")
        response = self.client.get(url)

        products = response.context["products"]

        self.assertIn(self.active_product, products)
        self.assertNotIn(self.inactive_product, products)


class CatalogDetailViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.active_product = Product.objects.create(
            name="Detalle Activo",
            description="Descripción detalle activo",
            category=Category.CABELLO,
            brand="Marca C",
            price=Decimal("29.99"),
            stock=20,
            is_active=True,
        )

        cls.inactive_product = Product.objects.create(
            name="Detalle Inactivo",
            description="Descripción detalle inactivo",
            category=Category.PERFUME,
            brand="Marca D",
            price=Decimal("39.99"),
            stock=0,
            is_active=False,
        )

    def test_catalog_detail_status_code_and_template(self):
        """
        El detalle de un producto activo devuelve 200 y usa
        la plantilla de detalle para usuario.
        """
        url = reverse("catalog_detail", args=[self.active_product.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "product/detail_user.html")
        self.assertContains(response, self.active_product.name)

    def test_catalog_detail_returns_404_for_inactive_product(self):
        """
        Si el producto está inactivo, el detalle del catálogo
        debe devolver 404.
        """
        url = reverse("catalog_detail", args=[self.inactive_product.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_catalog_detail_returns_404_for_nonexistent_product(self):
        """Si el producto no existe, también 404."""
        url = reverse("catalog_detail", args=[9999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class StockTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="user",
            email="user@example.com",
            password="pass1234",
            role="user",
        )
        cls.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="pass1234",
            role="admin",
        )

        cls.product_high = Product.objects.create(
            name="Producto Alto", stock=20, price=10
        )
        cls.product_low = Product.objects.create(
            name="Producto Bajo", stock=5, price=10
        )
        cls.product_out = Product.objects.create(
            name="Producto Agotado", stock=0, price=10
        )

        cls.stock_url = reverse("stock")
        cls.login_url = reverse("login")
        cls.dashboard_url = reverse("dashboard")

    # --- TESTS DE ACCESO ---

    def test_anonymous_user_redirects_to_dashboard(self):
        resp = self.client.get(self.stock_url)
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, self.dashboard_url)

    def test_non_admin_user_redirects_to_dashboard(self):
        self.client.login(email=self.user.email, password="pass1234")
        resp = self.client.get(self.stock_url)
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, self.dashboard_url)

    def test_admin_user_succeeds_get(self):
        self.client.login(email=self.admin.email, password="pass1234")
        resp = self.client.get(self.stock_url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "product/stock.html")

    # --- TESTS DE FUNCIONALIDAD ---

    def test_stock_page_shows_all_products(self):
        self.client.login(email=self.admin.email, password="pass1234")
        resp = self.client.get(self.stock_url)

        # Comprobamos que aparecen los 3 productos
        self.assertEqual(len(resp.context["products"]), 3)

        # Comprobamos el HTML
        self.assertContains(resp, "Producto Alto")
        self.assertContains(
            resp, '<span class="stock-ok">En Stock: 20</span>', html=True
        )

        self.assertContains(resp, "Producto Bajo")
        self.assertContains(
            resp, '<span class="stock-low">Stock Bajo: 5</span>', html=True
        )

        self.assertContains(resp, "Producto Agotado")
        self.assertContains(
            resp, '<span class="stock-out">Agotado (0)</span>', html=True
        )

    def test_post_admin_updates_stock_successfully(self):
        """5. CORRECTO: Un admin puede actualizar el stock (Test 7 en tu código)."""
        self.client.login(email=self.admin.email, password="pass1234")

        self.assertEqual(self.product_high.stock, 20)  # Stock inicial

        data = {"product_id": self.product_high.pk, "stock": 15}
        resp = self.client.post(
            self.stock_url, data, follow=True
        )  # Se hace una petición POST para actualizar el stock a 15

        # Comprobamos que volvemos a la página de stock
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "product/stock.html")

        # Comprobamos que la base de datos se actualizó correctamente
        self.product_high.refresh_from_db()
        self.assertEqual(self.product_high.stock, 15)

    def test_post_admin_invalid_product_returns_404(self):
        self.client.login(email=self.admin.email, password="pass1234")
        data = {"product_id": 999, "stock": 15}  # ID 999 no existe

        resp = self.client.post(self.stock_url, data)
        self.assertEqual(resp.status_code, 404)

    def test_post_admin_invalid_stock_value_shows_error(self):
        self.client.login(email=self.admin.email, password="pass1234")

        # Enviamos un valor de stock no numérico
        data = {"product_id": self.product_high.pk, "stock": "abc"}
        resp = self.client.post(self.stock_url, data, follow=True)

        # Comprobamos que volvemos a la página de stock
        self.assertEqual(resp.status_code, 200)

        # Comprobamos que el stock NO se actualizó
        self.product_high.refresh_from_db()
        self.assertEqual(self.product_high.stock, 20)

    def test_post_admin_negative_stock_value_shows_error(self):
        self.client.login(email=self.admin.email, password="pass1234")

        # Enviamos un valor de stock negativo y comprobamos el error
        data = {"product_id": self.product_high.pk, "stock": "-5"}
        resp = self.client.post(self.stock_url, data, follow=True)

        self.assertEqual(resp.status_code, 200)

        self.product_high.refresh_from_db()
        self.assertEqual(self.product_high.stock, 20)  # No cambia
