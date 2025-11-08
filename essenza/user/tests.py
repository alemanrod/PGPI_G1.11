from django.test import TestCase

# Create your tests here.
# user/tests/test_login.py
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

class LoginViewTests(TestCase):
    def setUp(self):
        # usuario de prueba
        self.username = "user1"
        self.email = "user1@example.com"
        self.password = "pass1234"
        self.user = User.objects.create_user(
            username=self.username,
            email=self.email,
            password=self.password
        )
        self.login_url = reverse("user:login")  
        self.home_url = reverse("home")     
        self.escaparate_url = reverse("escaparate")

    #1. comprueba que la pagina de login carga correctamente
    def test_get_login_page_returns_200(self):
        resp = self.client.get(self.login_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Iniciar sesión")  
        self.assertContains(resp, "ESSENZA")      

    #2. si email y contraseña validas redirige al escaparate
    def test_login_with_valid_email_redirects_escaparate(self):
        data = {"email": self.email, "password": self.password}
        resp = self.client.post(self.login_url, data, follow=False)
        self.assertEqual(resp.status_code, 302, resp.content)
        self.assertEqual(resp["Location"], self.escaparate_url)

    #3. si email y contraseña no validas muestra error
    def test_login_with_invalid_passwordAndEmail_shows_error(self):
        data = {"email": "wrong", "password": "wrong"}
        resp = self.client.post(self.login_url, data)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Usuario o contraseña incorrectos")

    #4. si email no es valido muestra error
    def test_login_with_invalid_email_shows_error(self):
        data = {"email": "wrong", "password": self.password}
        resp = self.client.post(self.login_url, data)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Usuario o contraseña incorrectos")

    #5. si contraseña no es valida muestra error
    def test_login_with_invalid_password_shows_error(self):
        data = {"email": self.email, "password": "wrong"}
        resp = self.client.post(self.login_url, data)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Usuario o contraseña incorrectos")
