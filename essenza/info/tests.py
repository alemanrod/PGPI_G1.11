from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from order.models import Order, OrderProduct, Status
from product.models import Product

User = get_user_model()


class SalesReportsViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = User.objects.create(
            username="admin_test",
            email="admin@test.com",
            password="password",
            role="admin",
        )
        cls.staff_user = User.objects.create(
            username="staff_test",
            email="staff@test.com",
            password="password",
            role="staff",
        )
        cls.client_user = User.objects.create(
            username="client_test",
            email="client@test.com",
            password="password",
            role="client",
        )
        cls.admin_user.set_password("password")
        cls.admin_user.save()
        cls.client_user.set_password("password")
        cls.client_user.save()

        cls.prod1 = Product.objects.create(name="Vela", price=10.00, stock=50)
        cls.prod2 = Product.objects.create(name="Jabon", price=5.00, stock=100)

        cls.order1 = Order.objects.create(
            user=cls.client_user,
            email="client@test.com",
            address="Calle Falsa 123",
            status=Status.ENTREGADO,
            placed_at=timezone.now() - timezone.timedelta(days=2),
        )
        cls.order2 = Order.objects.create(
            user=cls.admin_user,
            email="admin@test.com",
            address="Calle Real 456",
            status=Status.ENVIADO,
            placed_at=timezone.now() - timezone.timedelta(days=1),
        )
        OrderProduct.objects.create(order=cls.order1, product=cls.prod1, quantity=10)
        OrderProduct.objects.create(order=cls.order1, product=cls.prod2, quantity=5)
        OrderProduct.objects.create(order=cls.order2, product=cls.prod1, quantity=3)

        cls.history_url = reverse("info:sales_reports_view", args=["history"])
        cls.product_url = reverse("info:sales_reports_view", args=["product"])
        cls.user_url = reverse("info:sales_reports_view", args=["user"])

    def test_unauthenticated_access_is_denied(self):
        self.client.logout()
        response = self.client.get(self.history_url)
        self.assertEqual(response.status_code, 403)

    def test_non_admin_user_gets_forbidden_403(self):
        self.client.force_login(self.client_user)
        response = self.client.get(self.history_url)
        self.assertEqual(response.status_code, 403)

    def test_access_granted_to_admin_user(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(self.history_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "info/reports_master.html")

    def test_report_with_no_sales(self):
        """Asegura que el reporte funciona (200 OK) cuando no hay órdenes en la DB."""
        Order.objects.all().delete()

        self.client.force_login(self.admin_user)
        response = self.client.get(self.history_url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("orders", response.context)
        self.assertEqual(response.context["orders"].count(), 0)
        response_product = self.client.get(self.product_url)
        self.assertEqual(response_product.status_code, 200)
        self.assertEqual(response_product.context["sales_data"].count(), 0)

    def test_report_excludes_null_users(self):
        """Asegura que los pedidos sin usuario (anónimos) son excluidos del reporte de usuario."""
        Order.objects.create(
            user=None, email="anon@test.com", address="Unknown", status=Status.ENVIADO
        )

        self.client.force_login(self.admin_user)
        response = self.client.get(self.user_url)
        self.assertEqual(response.context["sales_data"].count(), 2)

        emails = [item["user__email"] for item in response.context["sales_data"]]
        self.assertNotIn(None, emails)

    def test_template_names_are_correct(self):
        """Verifica que la plantilla de contenido y el título son correctos para cada tipo."""
        self.client.force_login(self.admin_user)
        response_h = self.client.get(self.history_url)
        self.assertEqual(response_h.context["template_name"], "info/sales_history.html")
        self.assertEqual(
            response_h.context["report_title"], "Historial Completo de Ventas"
        )
        response_p = self.client.get(self.product_url)
        self.assertEqual(response_p.context["template_name"], "info/product_sales.html")
        self.assertEqual(
            response_p.context["report_title"], "Ventas Totales por Producto"
        )
        response_u = self.client.get(self.user_url)
        self.assertEqual(response_u.context["template_name"], "info/user_sales.html")
        self.assertEqual(
            response_u.context["report_title"], "Ventas Totales por Usuario"
        )
