from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from product.models import Product
from order.models import Order, OrderProduct, Status


User = get_user_model()


class CartTests(TestCase):
	def setUp(self):
		self.client = Client()
		# Create a sample product
		self.product = Product.objects.create(
			name="Test Product",
			description="Desc",
			category="maquillaje",
			brand="Marca",
			price="9.99",
			stock=10,
			is_active=True,
		)

		# Regular user
		self.user = User.objects.create_user(
			email="user@example.com", username="user1", password="pass1234", role="user"
		)

		# Admin user
		self.admin = User.objects.create_user(
			email="admin@example.com", username="admin1", password="adminpass", role="admin", is_staff=True
		)

	def test_anonymous_add_to_cart_creates_session(self):
		url = reverse('add_to_cart', kwargs={'product_pk': self.product.pk})
		response = self.client.post(url, {'quantity': 2}, follow=True)

		# Should redirect to cart_detail
		self.assertEqual(response.status_code, 200)
		session = self.client.session
		self.assertIn('cart_session', session)
		cart = session['cart_session']
		self.assertIn(str(self.product.pk), cart)
		self.assertEqual(cart[str(self.product.pk)]['quantity'], 2)

	def test_authenticated_user_adds_to_db_cart(self):
		self.client.login(email='user@example.com', password='pass1234')
		url = reverse('add_to_cart', kwargs={'product_pk': self.product.pk})
		response = self.client.post(url, {'quantity': 3}, follow=True)

		# After adding, there should be a pending Order for the user
		self.assertEqual(response.status_code, 200)
		orders = Order.objects.filter(user=self.user, status=Status.PENDING)
		self.assertTrue(orders.exists())
		order = orders.first()
		# Check OrderProduct exists
		op = OrderProduct.objects.filter(order=order, product=self.product).first()
		self.assertIsNotNone(op)
		self.assertEqual(op.quantity, 3)

	def test_admin_get_cart_forbidden(self):
		# Admin should get 403 on cart detail
		self.client.login(email='admin@example.com', password='adminpass')
		url = reverse('cart_detail')
		response = self.client.get(url)
		self.assertEqual(response.status_code, 403)

	def test_admin_cannot_add_to_cart(self):
		self.client.login(email='admin@example.com', password='adminpass')
		url = reverse('add_to_cart', kwargs={'product_pk': self.product.pk})
		response = self.client.post(url)
		self.assertEqual(response.status_code, 403)

	def test_cart_shows_empty_after_order_deleted(self):
		# Create a pending order for the user with one OrderProduct
		order = Order.objects.create(user=self.user, status=Status.PENDING, address='')
		OrderProduct.objects.create(order=order, product=self.product, quantity=2)

		# Delete the order
		order.delete()

		# Login as user and request cart detail
		self.client.login(email='user@example.com', password='pass1234')
		url = reverse('cart_detail')
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)
		self.assertIn('cart_items', response.context)
		self.assertEqual(len(response.context['cart_items']), 0)

