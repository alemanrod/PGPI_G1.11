# Create your tests here.
from django.test import TestCase


# Create your tests here.
from django.urls import reverse
from .models import Product


class ProductCRUDTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name='Test Product',
            description='A product for testing',
            category='maquillaje',
            brand='TestBrand',
            price='9.99',
            stock=10,
            is_active=True,
        )
    def test_list_view(self):
        url = reverse('product_list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.product.name)


    def test_detail_view(self):
        url = reverse('product_detail', args=[self.product.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.product.description)


    def test_create_view(self):
        url = reverse('product_create')
        data = {
            'name': 'New Product',
            'description': 'Created in test',
            'category': 'perfume',
            'brand': 'BrandX',
            'price': '5.50',
            'stock': 3,
            'is_active': True,
        }
        resp = self.client.post(url, data)
        # redirección esperada tras creación
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Product.objects.filter(name='New Product').exists())


    def test_update_view(self):
        url = reverse('product_update', args=[self.product.pk])
        data = {
            'name': 'Updated Name',
            'description': self.product.description,
            'category': self.product.category,
            'brand': self.product.brand,
            'price': str(self.product.price),
            'stock': self.product.stock,
            'is_active': self.product.is_active,
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Updated Name')


    def test_delete_view(self):
        url = reverse('product_delete', args=[self.product.pk])
        # GET muestra el confirm, POST realiza borrado
        resp_get = self.client.get(url)
        self.assertEqual(resp_get.status_code, 200)
        resp_post = self.client.post(url)
        self.assertEqual(resp_post.status_code, 302)
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())