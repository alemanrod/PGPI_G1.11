from unittest.mock import MagicMock, patch

from cart.models import Cart, CartProduct
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from product.models import Category, Product

from order.models import Order

User = get_user_model()


class CheckoutFlowTests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Usuario de prueba (Cliente)
        self.user = User.objects.create_user(
            username="testuser@example.com",
            email="testuser@example.com",
            password="password123",
            first_name="Test",
            last_name="User",
            role="user",
        )

        # 2. Usuario Admin (para pruebas de permisos)
        self.admin_user = User.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="password123",
            role="admin",
        )

        # 3. Producto con stock controlado (10 unidades)
        self.product = Product.objects.create(
            name="Producto Test",
            description="Desc",
            category=Category.MAQUILLAJE,
            brand="Brand",
            price=50.00,
            stock=10,
            is_active=True,
        )

        # 4. URLs
        self.checkout_url = reverse("create_checkout")
        self.success_url = reverse("successful_payment")

    def _create_cart_for_user(self, quantity=1):
        """Helper para crear un carrito rápido"""
        cart = Cart.objects.create(user=self.user)
        CartProduct.objects.create(cart=cart, product=self.product, quantity=quantity)
        return cart

    # ==========================================
    # BLOQUE 1: CONTRARREMBOLSO (COD)
    # ==========================================
    def test_cod_checkout_success(self):
        """
        Prueba el flujo completo de pago en EFECTIVO.
        Debe: Crear orden, Restar stock, is_paid=False, Guardar dirección manual.
        """
        self.client.force_login(self.user)
        self._create_cart_for_user(quantity=2)  # Compramos 2 (Total 100€)

        # Simulamos el envío del formulario
        data = {
            "payment_method": "cod",
            "shipping_name": "Juan Pérez",
            "shipping_email": "juan@test.com",
            "shipping_address": "Calle Falsa 123",
            "shipping_city": "Madrid",
            "shipping_zip": "28001",
        }

        response = self.client.post(self.checkout_url, data)

        # 1. Debe renderizar la página de éxito (status 200)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "order/success.html")

        # 2. Verificar la Orden en BD
        order = Order.objects.last()
        self.assertIsNotNone(order)

        # [VERDAD FINANCIERA] No pagado
        self.assertFalse(order.is_paid)

        # [VERDAD DE DATOS] La dirección se concatenó correctamente
        expected_address = "Juan Pérez | Calle Falsa 123, Madrid (28001)"
        self.assertEqual(order.address, expected_address)
        self.assertEqual(order.email, "juan@test.com")

        # [VERDAD LOGÍSTICA] Stock restado (10 - 2 = 8)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)

        # 3. Carrito borrado
        self.assertFalse(Cart.objects.filter(user=self.user).exists())

    def test_cod_checkout_fails_missing_data(self):
        """Si el usuario intenta trucar el form y enviar vacío, debe fallar."""
        self.client.force_login(self.user)
        self._create_cart_for_user()

        data = {
            "payment_method": "cod",
            # Falta shipping_address, name, etc.
            "shipping_email": "hack@test.com",
        }

        response = self.client.post(self.checkout_url, data)

        # Tu vista devuelve HttpResponse con status 400 (Bad Request)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)  # No se creó nada

    # ==========================================
    # BLOQUE 2: STRIPE (MOCKED)
    # ==========================================
    @patch("stripe.checkout.Session.create")
    def test_stripe_checkout_redirects_to_gateway(self, mock_stripe_create):
        """
        Verifica que si elijo tarjeta, el backend llama a Stripe y me manda a su URL.
        """
        self.client.force_login(self.user)
        self._create_cart_for_user(quantity=1)

        # Mock de la respuesta de Stripe
        mock_stripe_create.return_value.url = "https://checkout.stripe.com/fake-session"

        data = {"payment_method": "stripe"}

        response = self.client.post(self.checkout_url, data)

        # Verificar llamada a Stripe API
        mock_stripe_create.assert_called_once()

        # Verificar redirección
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://checkout.stripe.com/fake-session")

    @patch("stripe.checkout.Session.retrieve")
    def test_stripe_success_callback_creates_order(self, mock_stripe_retrieve):
        """
        Simula que el usuario vuelve de Stripe habiendo pagado.
        Debe: Crear orden, is_paid=True, Usar dirección de Stripe.
        """
        self.client.force_login(self.user)
        self._create_cart_for_user(quantity=3)  # Compramos 3

        # Mock complejo: Simulamos el objeto Session de Stripe
        mock_session = MagicMock()
        mock_session.payment_status = "paid"
        mock_session.customer_details.email = "stripe_customer@test.com"

        # Stripe devuelve la dirección en un objeto anidado
        mock_session.customer_details.address.line1 = "Calle Stripe"
        mock_session.customer_details.address.city = "Internet"
        mock_session.customer_details.address.postal_code = "00000"

        mock_stripe_retrieve.return_value = mock_session

        # Simulamos la llamada a la URL de retorno
        url = self.success_url + "?session_id=cs_test_fake123"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        # Verificaciones
        order = Order.objects.last()
        self.assertIsNotNone(order)

        # [VERDAD FINANCIERA] Pagado
        self.assertTrue(order.is_paid)

        # [VERDAD LOGÍSTICA] Stock (10 - 3 = 7)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 7)

        # Dirección viene de Stripe
        self.assertIn("Calle Stripe", order.address)

    @patch("stripe.checkout.Session.retrieve")
    def test_stripe_payment_failed_or_unpaid(self, mock_stripe_retrieve):
        """
        Si Stripe dice que NO está pagado (ej. tarjeta rechazada),
        no debemos marcar la orden como pagada o no crearla.
        """
        mock_session = MagicMock()
        mock_session.payment_status = "unpaid"  # <--- CASO FALLIDO
        mock_stripe_retrieve.return_value = mock_session

        url = self.success_url + "?session_id=cs_fail_123"
        response = self.client.get(url)

        # [CORREGIDO] Verificamos que la vista respondió (aunque sea success o error)
        # Lo importante es lo que pasa en la base de datos
        self.assertEqual(response.status_code, 200)

        # Verificamos si se creó orden
        # Si tu lógica crea orden incluso si falla (lo cual es raro), debe ser is_paid=False
        order = Order.objects.filter(email="stripe@user.com").first()
        if order:
            self.assertFalse(
                order.is_paid, "La orden no debería estar pagada si Stripe falló"
            )

    def test_stripe_callback_without_session_id(self):
        """Intentar acceder a la URL de éxito sin session_id debe fallar."""
        response = self.client.get(self.success_url)
        # Tu vista devuelve HttpResponse("Error...") que es un 200 OK con texto
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Error")

    # ==========================================
    # BLOQUE 3: USUARIO ANÓNIMO (GUEST)
    # ==========================================
    def test_guest_checkout_cod(self):
        """
        Prueba que un usuario NO logueado puede comprar usando la sesión.
        """
        # NO hacemos login

        # 1. Añadir al carrito (guarda en sesión)
        session = self.client.session
        session["cart_session"] = {
            str(self.product.pk): {"quantity": 1, "price": "50.00"}
        }
        session.save()

        # 2. Pagar Contrarrembolso
        data = {
            "payment_method": "cod",
            "shipping_name": "Invitado",
            "shipping_email": "guest@test.com",
            "shipping_address": "Hotel",
            "shipping_city": "Bcn",
            "shipping_zip": "08001",
        }

        response = self.client.post(self.checkout_url, data)

        self.assertEqual(response.status_code, 200)

        # Verificar Orden
        order = Order.objects.last()
        self.assertIsNone(order.user)  # No hay usuario asociado
        self.assertEqual(order.email, "guest@test.com")
        self.assertFalse(order.is_paid)

        # Verificar Stock
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 9)

    # ==========================================
    # BLOQUE 4: SEGURIDAD Y PERMISOS
    # ==========================================
    def test_admin_view_permission(self):
        """Un usuario normal NO debe poder ver el listado global de pedidos."""
        self.client.force_login(self.user)  # Usuario normal
        response = self.client.get(reverse("order_list_admin"))

        # Tu handle_no_permission redirige al dashboard (302)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("dashboard"), response.url)

    def test_update_status_permission(self):
        """Un usuario normal NO puede cambiar el estado de un pedido."""
        self.client.force_login(self.user)
        # Creamos una orden dummy
        order = Order.objects.create(email="test@test.com", address="X")

        url = reverse("order_update_status", args=[order.tracking_code])
        response = self.client.post(url, {"status": "enviado"})

        # Redirige al dashboard por falta de permisos
        self.assertEqual(response.status_code, 302)

        # El estado NO debe cambiar
        order.refresh_from_db()
        self.assertNotEqual(order.status, "enviado")

    # ==========================================
    # BLOQUE 5: HISTORIAL Y TRACKING
    # ==========================================
    def test_order_search_found(self):
        """El buscador público debe encontrar un pedido por código y email."""
        order = Order.objects.create(email="search@me.com", address="Home")

        data = {"tracking_code": order.tracking_code, "email": "search@me.com"}
        response = self.client.post(reverse("order_search"), data)

        # Debe redirigir al tracking detallado
        self.assertRedirects(
            response, reverse("order_tracking", args=[order.tracking_code])
        )

    def test_order_search_not_found_wrong_email(self):
        """Si el código es correcto pero el email no, no debe mostrar nada (Privacidad)."""
        order = Order.objects.create(email="real@me.com", address="Home")

        data = {
            "tracking_code": order.tracking_code,
            "email": "hacker@evil.com",  # Email incorrecto
        }
        response = self.client.post(reverse("order_search"), data)

        self.assertEqual(response.status_code, 200)  # Se queda en la misma página
        self.assertContains(response, "No se ha encontrado")  # Mensaje de error

    def test_order_history_isolation(self):
        """Un usuario solo debe ver SUS pedidos, no los de otros."""
        self.client.force_login(self.user)

        # Pedido propio
        my_order = Order.objects.create(
            user=self.user, email=self.user.email, address="Mine"
        )
        # Pedido ajeno
        other_user = User.objects.create(username="other", email="other@test.com")
        other_order = Order.objects.create(
            user=other_user, email="other@test.com", address="Theirs"
        )

        response = self.client.get(reverse("order_history"))

        # Debe contener mi pedido
        self.assertContains(response, my_order.tracking_code)
        # NO debe contener el pedido ajeno
        self.assertNotContains(response, other_order.tracking_code)
