from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from product.models import Product, Category
from django.core.files.uploadedfile import SimpleUploadedFile  
from decimal import Decimal
User = get_user_model()


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
            photo= None,
            stock=5,
            category="maquillaje",
            is_active=True
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
        self.assertEqual(resp.status_code, 302)   # Redirigido por permisos

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
        url = reverse('product_list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Producto Test")


    def test_admin_can_access_detail(self):
        self.client.force_login(self.admin)
        url = reverse('product_detail', args=[self.product.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.product.name)

    def test_admin_can_delete_product(self):
        self.client.force_login(self.admin)
        url = reverse('product_delete', args=[self.product.pk])

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
