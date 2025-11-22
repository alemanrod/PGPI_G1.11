from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from product.models import Product, Category
from order.models import Order, OrderProduct, Status

User = get_user_model()


# ============================================================
# TESTS: LISTADO DE PEDIDOS DEL USUARIO
# ============================================================

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

        # Pedido 1 del usuario
        cls.order1 = Order.objects.create(
            user=cls.user,
            status=Status.EN_PREPARACION,
            address="Calle 1",
        )
        OrderProduct.objects.create(
            order=cls.order1,
            product=cls.product,
            quantity=2
        )

        # Pedido 2 del usuario
        cls.order2 = Order.objects.create(
            user=cls.user,
            status=Status.ENVIADO,
            address="Calle 2",
        )
        OrderProduct.objects.create(
            order=cls.order2,
            product=cls.product,
            quantity=1
        )

        # Pedido de otro usuario (NO debe salir)
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
        self.assertEqual(resp.status_code, 302)

    def test_user_sees_only_his_orders(self):
        """Debe ver TODOS sus pedidos, incluyendo EN_PREPARACION."""
        self.client.login(email="user@test.com", password="1234")
        resp = self.client.get(self.url)

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "order/order_list_user.html")

        orders = resp.context["orders"]
        self.assertEqual(orders.count(), 2)  # 🔥 YA NO FILTRAMOS NADA

        # Los IDs deben coincidir
        returned_ids = set(o.id for o in orders)
        expected_ids = {self.order1.id, self.order2.id}
        self.assertEqual(returned_ids, expected_ids)

        self.assertContains(resp, "Calle 1")
        self.assertContains(resp, "Calle 2")



# ============================================================
# TESTS: LISTADO DE PEDIDOS DEL ADMIN
# ============================================================

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



# ============================================================
# TESTS: SEGUIMIENTO DE PEDIDO
# ============================================================

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

        cls.url = reverse("order_track")

    def test_track_get_returns_form(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "order/order_track.html")

    def test_track_post_valid_redirects_to_detail(self):
        data = {"order_id": str(self.order.id), "email": "track@test.com"}
        resp = self.client.post(self.url, data, follow=True)

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "order/order_detail.html")
        self.assertContains(resp, "Direccion de prueba")

    def test_track_post_invalid_shows_error(self):
        data = {"order_id": "9999", "email": "track@test.com"}
        resp = self.client.post(self.url, data)

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "No se ha encontrado ningún pedido")



# ============================================================
# TESTS: DETALLE DE PEDIDO
# ============================================================

class OrderDetailViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()

        cls.user = User.objects.create_user(
            username="user_detail",
            email="user_detail@test.com",
            password="1234",
            role="user"
        )
        cls.other_user = User.objects.create_user(
            username="other_detail",
            email="other_detail@test.com",
            password="1234",
            role="user"
        )
        cls.admin = User.objects.create_user(
            username="admin_detail",
            email="admin_detail@test.com",
            password="1234",
            role="admin",
            is_staff=True
        )

        cls.product = Product.objects.create(
            name="Prod Detalle",
            brand="Brand",
            description="d",
            category=Category.MAQUILLAJE,
            price="7.00",
            stock=10,
            is_active=True,
        )

        cls.order = Order.objects.create(
            user=cls.user,
            status=Status.ENVIADO,
            address="Calle detalle",
        )
        OrderProduct.objects.create(
            order=cls.order,
            product=cls.product,
            quantity=2
        )

        cls.url = reverse("order_detail", args=[cls.order.id])

    def test_user_must_login(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)

    def test_owner_can_view_detail(self):
        self.client.login(email="user_detail@test.com", password="1234")
        resp = self.client.get(self.url)

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "order/order_detail.html")
        self.assertContains(resp, "Prod Detalle")

    def test_other_user_cannot_view_detail(self):
        self.client.login(email="other_detail@test.com", password="1234")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_view_any_detail(self):
        self.client.login(email="admin_detail@test.com", password="1234")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "order/order_detail.html")
