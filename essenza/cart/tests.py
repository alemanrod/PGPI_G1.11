from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from product.models import Category, Product

from cart.models import Cart, CartProduct

User = get_user_model()


class CartTests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Crear Usuario
        self.user = User.objects.create_user(
            username="user1",
            email="test@example.com",
            password="password123",
            first_name="Test",
            last_name="User",
        )

        # 2. Crear Producto
        self.product = Product.objects.create(
            name="Producto Test",
            description="Descripción de prueba",
            category=Category.MAQUILLAJE,
            brand="Marca Test",
            price=10.00,
            stock=50,
            is_active=True,
        )

        # 3. URLs
        self.url_detail = reverse("cart_detail")
        self.url_add = reverse("add_to_cart", args=[self.product.pk])
        self.url_update = reverse("update_cart_item", args=[self.product.pk])
        self.url_remove = reverse("remove_from_cart", args=[self.product.pk])

        # URL ficticia para simular el "referer" (la página anterior)
        self.url_catalog = reverse("catalog")

    # ---------------------------------------------------------
    # BLOQUE 1: DETALLE DEL CARRITO (GET)
    # ---------------------------------------------------------

    def test_cart_detail_authenticated_empty(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url_detail)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context.get("cart_products", [])), 0)

    def test_cart_detail_authenticated_with_items(self):
        self.client.force_login(self.user)
        cart = Cart.objects.create(user=self.user)
        CartProduct.objects.create(cart=cart, product=self.product, quantity=2)

        response = self.client.get(self.url_detail)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["cart_products"]), 1)
        self.assertEqual(response.context["subtotal"], 20.00)

    def test_cart_detail_anonymous_session(self):
        self.client.logout()
        session = self.client.session
        session["cart_session"] = {
            str(self.product.pk): {"quantity": 3, "price": "10.00"}
        }
        session.save()

        response = self.client.get(self.url_detail)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["cart_products"]), 1)
        self.assertEqual(response.context["subtotal"], 30.00)

    # ---------------------------------------------------------
    # BLOQUE 2: AÑADIR AL CARRITO (POST) - ACTUALIZADO
    # ---------------------------------------------------------

    def test_add_item_action_buy_redirects_to_cart(self):
        """
        Prueba el flujo 'Comprar ahora' (action='buy').
        Debe añadir el producto y redirigir al carrito.
        """
        self.client.force_login(self.user)

        # Enviamos action='buy' explícitamente
        response = self.client.post(self.url_add, {"quantity": 1, "action": "buy"})

        # Debe redirigir a cart_detail
        self.assertRedirects(response, self.url_detail)

        # Verificar DB
        cart = Cart.objects.get(user=self.user)
        cp = CartProduct.objects.get(cart=cart, product=self.product)
        self.assertEqual(cp.quantity, 1)

    def test_add_item_action_add_stays_on_page(self):
        """
        Prueba el flujo 'Añadir al carrito' (action='add').
        Debe añadir el producto y redirigir a la página anterior (Referer).
        """
        self.client.force_login(self.user)

        # Simulamos que venimos del catálogo
        referer = self.url_catalog

        # Enviamos action='add' y el HTTP_REFERER
        response = self.client.post(
            self.url_add, {"quantity": 2, "action": "add"}, HTTP_REFERER=referer
        )

        # Debe redirigir DE VUELTA al catálogo, no al carrito
        self.assertRedirects(response, referer)

        # Verificar DB
        cart = Cart.objects.get(user=self.user)
        cp = CartProduct.objects.get(cart=cart, product=self.product)
        self.assertEqual(cp.quantity, 2)

        # Verificar mensajes (feedback visual)
        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertIn("añadido al carrito", str(messages[0]))

    def test_add_item_anonymous(self):
        """Añadir ítem guarda en Sesión (usando 'buy' para verificar redirect clásico)."""
        self.client.logout()

        response = self.client.post(self.url_add, {"quantity": 1, "action": "buy"})

        self.assertRedirects(response, self.url_detail)

        session = self.client.session
        self.assertIn("cart_session", session)
        self.assertEqual(session["cart_session"][str(self.product.pk)]["quantity"], 1)

    def test_add_item_out_of_stock(self):
        """No se debe poder añadir productos sin stock."""
        self.product.stock = 0
        self.product.save()

        self.client.force_login(self.user)

        # Simulamos venir del catálogo
        referer = self.url_catalog
        response = self.client.post(self.url_add, {"quantity": 1}, HTTP_REFERER=referer)

        # Debe redirigir atrás con error
        self.assertRedirects(response, referer)

        # Verificar mensaje de error
        messages = list(response.wsgi_request._messages)
        self.assertIn("agotado", str(messages[0]).lower())

        # Verificar que NO se creó nada en DB
        self.assertFalse(CartProduct.objects.filter(product=self.product).exists())

    # ---------------------------------------------------------
    # BLOQUE 3: ACTUALIZAR (POST)
    # ---------------------------------------------------------

    def test_auth_update_item(self):
        self.client.force_login(self.user)
        cart = Cart.objects.create(user=self.user)

        # TRUCO: Forzamos que el ID del CartProduct sea igual al del Product
        cp = CartProduct(
            id=self.product.pk, cart=cart, product=self.product, quantity=1
        )
        cp.save()

        response = self.client.post(self.url_update, {"quantity": 5})

        self.assertRedirects(response, self.url_detail)
        cp.refresh_from_db()
        self.assertEqual(cp.quantity, 5)

    def test_anon_update_item(self):
        self.client.logout()
        # Añadimos primero (action buy para ir al carrito)
        self.client.post(self.url_add, {"quantity": 1, "action": "buy"})

        # Actualizamos
        response = self.client.post(self.url_update, {"quantity": 4})

        self.assertRedirects(response, self.url_detail)
        session = self.client.session
        self.assertEqual(session["cart_session"][str(self.product.pk)]["quantity"], 4)

    # ---------------------------------------------------------
    # BLOQUE 4: ELIMINAR (POST)
    # ---------------------------------------------------------

    def test_auth_remove_item(self):
        self.client.force_login(self.user)
        cart = Cart.objects.create(user=self.user)

        # TRUCO: ID CartProduct == ID Product
        cp = CartProduct(
            id=self.product.pk, cart=cart, product=self.product, quantity=1
        )
        cp.save()

        response = self.client.post(self.url_remove)

        self.assertRedirects(response, self.url_detail)
        self.assertFalse(CartProduct.objects.filter(pk=cp.pk).exists())

    def test_anon_remove_item(self):
        self.client.logout()
        # Setup sesión
        session = self.client.session
        session["cart_session"] = {
            str(self.product.pk): {"quantity": 1, "price": "10.00"}
        }
        session.save()

        response = self.client.post(self.url_remove)

        self.assertRedirects(response, self.url_detail)
        session = self.client.session
        self.assertNotIn(str(self.product.pk), session["cart_session"])
