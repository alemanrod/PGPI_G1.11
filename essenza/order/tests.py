from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from product.models import Category, Product

from order.models import Order, OrderProduct, Status

User = get_user_model()


# ============================================================
# TESTS: LISTADO DE PEDIDOS DEL USUARIO
# ============================================================


class OrderListUserViewTests(TestCase):
    @classmethod
    def setUpTestData(self):
        self.client = Client()

        # Creamos usuario
        self.user = User.objects.create_user(
            username="user1", email="user@test.com", password="1234"
        )
        # Asignamos rol manualmente por seguridad
        self.user.role = "user"
        self.user.save()

        self.other_user = User.objects.create_user(
            username="user2", email="user2@test.com", password="1234"
        )
        self.other_user.role = "user"
        self.other_user.save()

        self.product = Product.objects.create(
            name="Producto A",
            price="10.00",
            stock=10,
            is_active=True,
            category=Category.MAQUILLAJE,
            brand="Marca A",
        )

        # 1. Pedido visible del usuario (ENVIADO)
        self.order_user = Order.objects.create(
            user=self.user,
            email=self.user.email,  # Importante: ahora el modelo usa email
            status=Status.ENVIADO,
            address="Calle 1",
        )
        OrderProduct.objects.create(
            order=self.order_user, product=self.product, quantity=2
        )

        # 2. Pedido del usuario OCULTO (EN_PREPARACION - según la lógica de tu vista)
        self.order_hidden = Order.objects.create(
            user=self.user,
            email=self.user.email,
            status=Status.EN_PREPARACION,
            address="Calle Oculta",
        )
        OrderProduct.objects.create(
            order=self.order_hidden, product=self.product, quantity=1
        )

        # 3. Pedido de otro usuario (No debe verse)
        self.order_other = Order.objects.create(
            user=self.other_user,
            email=self.other_user.email,
            status=Status.ENVIADO,
            address="Otra calle",
        )
        OrderProduct.objects.create(
            order=self.order_other, product=self.product, quantity=1
        )

        # Asumiendo que la URL se llama 'order_history' en urls.py
        try:
            self.url = reverse("order_history")
        except Exception:
            self.url = "/order/history/"  # Fallback si no existe el name

    def test_user_must_login(self):
        """Un usuario anónimo debe ser redirigido al login."""
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue("login" in resp.url)


# ============================================================
# TESTS: LISTADO DE PEDIDOS DEL ADMIN
# ============================================================


class OrderListAdminViewTests(TestCase):
    @classmethod
    def setUpTestData(self):
        self.client = Client()

        # Admin
        self.admin = User.objects.create_user(
            username="admin1", email="admin@test.com", password="1234"
        )
        self.admin.role = "admin"
        self.admin.save()

        # User normal
        self.user = User.objects.create_user(
            username="user3", email="user3@test.com", password="1234"
        )
        self.user.role = "user"
        self.user.save()

        self.product = Product.objects.create(
            name="Prod",
            price="5.00",
            stock=10,
            is_active=True,
            category=Category.PERFUME,
            brand="Brand",
        )

        # Creamos un pedido para probar
        self.order = Order.objects.create(
            user=self.user,
            email="cliente@test.com",
            status=Status.ENVIADO,
            address="Dir Admin Test",
        )
        OrderProduct.objects.create(order=self.order, product=self.product, quantity=1)

        try:
            self.url = reverse("order_list_admin")
        except Exception:
            self.url = "/order/list/"

    def test_anonymous_redirects_to_login(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue("login" in resp.url)

    def test_admin_can_view_orders(self):
        self.client.login(email="admin@test.com", password="1234")
        resp = self.client.get(self.url)

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "order/order_list_admin.html")
        self.assertContains(resp, "Prod")
        self.assertContains(
            resp, self.order.tracking_code
        )  # Debe salir el tracking code


class OrderTrackViewTests(TestCase):
    @classmethod
    def setUpTestData(self):
        self.client = Client()

        self.product = Product.objects.create(
            name="Producto Track",
            price="12.00",
            stock=5,
            is_active=True,
            category=Category.CABELLO,
            brand="Marca Track",
        )

        # Creamos un pedido sin usuario (invitado) para probar el tracking público
        self.order = Order.objects.create(
            user=None,
            email="track@test.com",
            status=Status.ENVIADO,
            address="Direccion de prueba",
        )
        OrderProduct.objects.create(order=self.order, product=self.product, quantity=1)

        # URL de la vista de búsqueda (donde está el formulario)
        # Asumiendo que en urls.py se llama 'order_search'
        try:
            self.url_search = reverse("order_search")
        except Exception:
            self.url_search = "/order/search/"

    def test_track_get_returns_form(self):
        """GET debe mostrar el formulario vacío."""
        resp = self.client.get(self.url_search)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "order/order_search.html")
        self.assertFalse(resp.context["searched"])

    def test_track_post_valid_redirects_to_detail(self):
        """POST correcto debe REDIRIGIR a la vista de detalle."""
        # Usamos los nombres de campo exactos de tu HTML: 'tracking_code' y 'email'
        data = {"tracking_code": self.order.tracking_code, "email": "track@test.com"}
        resp = self.client.post(self.url_search, data)

        # Tu vista hace: return redirect("order_tracking", ...) -> Código 302
        self.assertEqual(resp.status_code, 302)

        # Verificamos que redirige a la URL con el tracking code
        # Asumiendo que la url de detalle es /order/track/<code:str>/
        expected_url = reverse("order_tracking", args=[self.order.tracking_code])
        self.assertRedirects(resp, expected_url)

    def test_track_post_invalid_shows_error(self):
        """POST con datos incorrectos muestra error en la misma página."""
        data = {
            "tracking_code": "wrong",  # Código falso
            "email": "track@test.com",
        }
        resp = self.client.post(self.url_search, data)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["searched"])  # Indica que se intentó buscar
