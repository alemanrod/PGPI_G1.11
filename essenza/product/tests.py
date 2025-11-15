from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from product.models import Product
from django.core.files.uploadedfile import SimpleUploadedFile  

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

