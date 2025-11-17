import io
import os

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class LoginViewTests(TestCase):
    def setUp(self):
        # usuario de prueba
        self.username = "user1"
        self.email = "user1@example.com"
        self.password = "pass1234"
        self.user = User.objects.create_user(
            username=self.username, email=self.email, password=self.password
        )
        self.login_url = reverse("login")
        self.dashboard_url = reverse("dashboard")

    # 1. comprueba que la pagina de login carga correctamente
    def test_get_login_page_returns_200(self):
        resp = self.client.get(self.login_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Iniciar sesión")
        self.assertContains(resp, "ESSENZA")

    # 2. si email y contraseña validas redirige al dashboard
    def test_login_with_valid_email_redirects_dashboard(self):
        data = {"email": self.email, "password": self.password}
        resp = self.client.post(self.login_url, data, follow=False)
        self.assertEqual(resp.status_code, 302, resp.content)
        self.assertEqual(resp["Location"], self.dashboard_url)

    # 3. si email y contraseña no validas muestra error
    def test_login_with_invalid_passwordAndEmail_shows_error(self):
        data = {"email": "wrong", "password": "wrong"}
        resp = self.client.post(self.login_url, data)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Usuario o contraseña incorrectos")

    # 4. si email no es valido muestra error
    def test_login_with_invalid_email_shows_error(self):
        data = {"email": "wrong", "password": self.password}
        resp = self.client.post(self.login_url, data)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Usuario o contraseña incorrectos")

    # 5. si contraseña no es valida muestra error
    def test_login_with_invalid_password_shows_error(self):
        data = {"email": self.email, "password": "wrong"}
        resp = self.client.post(self.login_url, data)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Usuario o contraseña incorrectos")


class RegisterViewTests(TestCase):
    def setUp(self):
        self.register_url = reverse("register")
        self.dashboard_url = reverse("dashboard")
        self.initial_user_count = User.objects.count()

        # Datos para un nuevo usuario de prueba
        self.valid_data = {
            "first_name": "Juan",
            "last_name": "Perez",
            "username": "nuevo_usuario",
            "email": "nuevo@ejemplo.com",
            "password1": "PasswordSeguro123",
            "password2": "PasswordSeguro123",
        }

    # 1. Comprueba que la página de registro carga correctamente
    def test_get_register_page_returns_200(self):
        resp = self.client.get(self.register_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Crear cuenta")
        self.assertContains(resp, "ESSENZA")

    # 2. Registro con datos válidos y redirige al dashboard (302)
    def test_successful_registration_redirects_and_creates_user(self):
        data = self.valid_data.copy()
        resp = self.client.post(self.register_url, data, follow=False)

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], self.dashboard_url)
        self.assertEqual(User.objects.count(), self.initial_user_count + 1)

        new_user = User.objects.get(email=data["email"])
        self.assertTrue(
            new_user.check_password(data["password1"])
        )  # La contraseña está hasheada

    # 3. Registro con email duplicado muestra error
    def test_registration_with_duplicate_email_shows_error(self):
        User.objects.create_user(
            username="test", email=self.valid_data["email"], password="test"
        )  # Usuario previo creado con mismo email
        data = self.valid_data.copy()
        resp = self.client.post(
            self.register_url, data
        )  # Intento de registro con el mismo email

        self.assertEqual(
            User.objects.count(), self.initial_user_count + 1
        )  # Solo se añade el usuario creado antes
        self.assertContains(resp, "Ya existe Usuario con este Email.", html=True)

    # 4. Registro con contraseñas que no coinciden muestra error
    def test_registration_with_mismatched_passwords_shows_error(self):
        data = self.valid_data.copy()
        data["password2"] = "diferente123"
        resp = self.client.post(self.register_url, data)

        self.assertEqual(User.objects.count(), self.initial_user_count)
        self.assertContains(resp, "Los dos campos de contraseña no coinciden.")

    # 5. Registro con campo 'first_name' vacío muestra error (required=True)
    def test_registration_missing_first_name_shows_error(self):
        data = self.valid_data.copy()
        data["first_name"] = ""
        resp = self.client.post(self.register_url, data)

        self.assertEqual(User.objects.count(), self.initial_user_count)
        self.assertContains(resp, "Este campo es obligatorio.")

    # 6. Registro con subida de foto válida
    def test_registration_with_valid_photo(self):
        # Creo una foto JPEG en memoria
        try:
            from PIL import Image

            buf = io.BytesIO()
            img = Image.new("RGB", (1, 1), color=(255, 0, 0))
            img.save(buf, format="JPEG")
            image_data = buf.getvalue()
        except Exception:
            self.skipTest("Pillow is required to create a test JPEG image")

        photo = SimpleUploadedFile(
            name="test_photo.jpg", content=image_data, content_type="image/jpeg"
        )

        data = self.valid_data.copy()
        data["photo"] = photo
        resp = self.client.post(self.register_url, data, follow=False)

        self.assertEqual(resp.status_code, 302)
        new_user = User.objects.get(email=data["email"])
        self.assertTrue(new_user.photo.name.startswith("profile_pics/test_photo"))

        # Elimina la foto creada
        if new_user.photo:
            if os.path.exists(new_user.photo.path):
                os.remove(new_user.photo.path)

    # 7. Registro sin campo 'foto' (opcional) es exitoso
    def test_registration_without_photo_is_successful(self):
        data = self.valid_data.copy()
        if "photo" in data:
            del data["photo"]

        resp = self.client.post(self.register_url, data, follow=False)

        self.assertEqual(resp.status_code, 302)
        new_user = User.objects.get(email=data["email"])
        self.assertFalse(new_user.photo)


class LogoutViewTests(TestCase):
    def setUp(self):
        self.client = self.client = self.client = self.client_class()
        self.user = User.objects.create_user(
            username="userlogout", email="logout@example.com", password="testlogout123"
        )
        self.login_url = reverse("login")
        self.logout_url = reverse("logout")
        self.dashboard_url = reverse("dashboard")

    # 1. Comprobar que un usuario logueado se desloguea y redirige correctamente
    def test_logout_redirects_to_dashboard_and_clears_session(self):
        # Iniciar sesión
        self.client.login(username="logout@example.com", password="testlogout123")

        # Verificar que la sesión está activa
        self.assertIn("_auth_user_id", self.client.session)

        # Hacer logout
        response = self.client.get(self.logout_url)

        # Verificar redirección al dashboard
        self.assertRedirects(response, self.dashboard_url)

        # Verificar que se ha cerrado la sesión
        self.assertNotIn("_auth_user_id", self.client.session)

    # 2. Comprobar que el logout borra la cookie de sesión
    def test_logout_deletes_session_cookie(self):
        """El logout deja la cookie de sesión vacía y expirada."""
        self.client.login(username="logout@example.com", password="testlogout123")
        response = self.client.get(self.logout_url)

        # Django deja la cookie 'sessionid', pero vacía o marcada para expirar
        self.assertIn("sessionid", response.cookies)
        cookie = response.cookies["sessionid"]
        self.assertTrue(
            cookie.value == "" or cookie["max-age"] == 0 or cookie["expires"]
        )
        self.assertRedirects(response, self.dashboard_url)

    # 3. Comprobar que un usuario no autenticado también redirige correctamente
    def test_logout_redirects_even_if_not_authenticated(self):
        response = self.client.get(self.logout_url)
        self.assertRedirects(response, self.dashboard_url)
