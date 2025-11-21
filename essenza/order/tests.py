from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from product.models import Product, Category
from order.models import Order, OrderProduct, Status

User = get_user_model()


class OrderListUserViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()

        cls.user = User.objects.create_user(
            username="user1",
            email="user@test.com",
            password="1234",
            role="user"
        )
        cls.other_user = User.objects.create_user(
            username="user2",
            email="user2@test.com",
            password="1234",
            role="user"
        )

        cls.product = Product.objects.create(
            name="Producto A",
            brand="Marca A",
            description="Desc",
            category=Category.MAQUILLAJE,
            price="10.00",
            stock=10,
            is_active=True,
        )

        # Pedido visible (NO en preparación) del usuario
        cls.order_user = Order.objects.create(
            user=cls.user,
            status=Status.ENVIADO,
            address="Calle 1",
        )
        OrderProduct.objects.create(
            order=cls.order_user,
            product=cls.product,
            quantity=2
        )

        # Pedido del usuario que NO debe salir (EN_PREPARACION)
        cls.order_hidden = Order.objects.create(
            user=cls.user,
            status=Status.EN_PREPARACION,
            address="Calle Oculta",
        )
        OrderProduct.objects.create(
            order=cls.order_hidden,
            product=cls.product,
            quantity=1
        )

        # Pedido de otro usuario
        cls.order_other = Order.objects.create(
            user=cls.other_user,
            status=Status.ENVIADO,
            address="Otra calle",
        )
        OrderProduct.objects.create(
            order=cls.order_other,
            product=cls.product,
            quantity=1
        )

        cls.url = reverse("order_list_user")

    def test_user_must_login(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)  # redirect a login

    def test_user_sees_only_his_non_preparacion_orders(self):
        self.client.login(email="user@test.com", password="1234")
        resp = self.client.get(self.url)

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "order/order_list_user.html")

        orders = resp.context["orders"]
        self.assertEqual(orders.count(), 1)
        self.assertEqual(orders.first().id, self.order_user.id)

        self.assertContains(resp, "Producto A")
        self.assertContains(resp, "Calle 1")


class OrderListAdminViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()

        cls.admin = User.objects.create_user(
            username="admin1",
            email="admin@test.com",
            password="1234",
            role="admin",
            is_staff=True
        )

        cls.user = User.objects.create_user(
            username="user3",
            email="user3@test.com",
            password="1234",
            role="user"
        )

        cls.product = Product.objects.create(
            name="Prod",
            brand="Brand",
            description="d",
            category=Category.PERFUME,
            price="5.00",
            stock=10,
            is_active=True,
        )

        cls.order = Order.objects.create(
            user=cls.user,
            status=Status.ENVIADO,
            address="Dir",
        )
        OrderProduct.objects.create(
            order=cls.order,
            product=cls.product,
            quantity=1
        )

        cls.url = reverse("order_list_admin")

    def test_admin_must_login(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)

    def test_admin_can_view_orders(self):
        self.client.login(email="admin@test.com", password="1234")
        resp = self.client.get(self.url)

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "order/order_list_admin.html")
        self.assertContains(resp, "Prod")
        self.assertContains(resp, "user3@test.com")


class OrderTrackViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()

        cls.user = User.objects.create_user(
            username="trackuser",
            email="track@test.com",
            password="1234",
            role="user"
        )

        cls.product = Product.objects.create(
            name="Producto Track",
            brand="Marca Track",
            description="Desc",
            category=Category.CABELLO,
            price="12.00",
            stock=5,
            is_active=True,
        )

        cls.order = Order.objects.create(
            user=cls.user,
            status=Status.ENVIADO,
            address="Direccion de prueba",
        )
        OrderProduct.objects.create(
            order=cls.order,
            product=cls.product,
            quantity=1
        )

        cls.url = reverse("order_track")  # ⬅️ SIN args

    def test_track_get_returns_form(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "order/order_track.html")

    def test_track_post_valid_shows_order(self):
        data = {"order_id": str(self.order.id), "email": "track@test.com"}
        resp = self.client.post(self.url, data)

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Direccion de prueba")
        self.assertContains(resp, self.order.get_status_display())

    def test_track_post_invalid_shows_error(self):
        data = {"order_id": "9999", "email": "track@test.com"}
        resp = self.client.post(self.url, data)

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "No se ha encontrado ningún pedido")
