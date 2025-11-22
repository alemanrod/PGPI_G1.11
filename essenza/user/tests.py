import io
import os

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

# UNIFICACIÓN: Usamos 'Usuario' para todo el archivo
Usuario = get_user_model()


class LoginViewTests(TestCase):
    def setUp(self):
        # usuario de prueba
        self.username = "user1"
        self.email = "user1@example.com"
        self.password = "pass1234"
        self.user = Usuario.objects.create_user(
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
        self.initial_user_count = Usuario.objects.count()

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
        self.assertEqual(Usuario.objects.count(), self.initial_user_count + 1)

        new_user = Usuario.objects.get(email=data["email"])
        self.assertTrue(
            new_user.check_password(data["password1"])
        )  # La contraseña está hasheada

    # 3. Registro con email duplicado muestra error
    def test_registration_with_duplicate_email_shows_error(self):
        Usuario.objects.create_user(
            username="test", email=self.valid_data["email"], password="test"
        )  # Usuario previo creado con mismo email
        data = self.valid_data.copy()
        resp = self.client.post(
            self.register_url, data
        )  # Intento de registro con el mismo email

        self.assertEqual(
            Usuario.objects.count(), self.initial_user_count + 1
        )  # Solo se añade el usuario creado antes
        self.assertContains(resp, "Ya existe Usuario con este Email.", html=True)

    # 4. Registro con contraseñas que no coinciden muestra error
    def test_registration_with_mismatched_passwords_shows_error(self):
        data = self.valid_data.copy()
        data["password2"] = "diferente123"
        resp = self.client.post(self.register_url, data)

        self.assertEqual(Usuario.objects.count(), self.initial_user_count)
        self.assertContains(resp, "Los dos campos de contraseña no coinciden.")

    # 5. Registro con campo 'first_name' vacío muestra error (required=True)
    def test_registration_missing_first_name_shows_error(self):
        data = self.valid_data.copy()
        data["first_name"] = ""
        resp = self.client.post(self.register_url, data)

        self.assertEqual(Usuario.objects.count(), self.initial_user_count)
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
        new_user = Usuario.objects.get(email=data["email"])
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
        new_user = Usuario.objects.get(email=data["email"])
        self.assertFalse(new_user.photo)


class LogoutViewTests(TestCase):
    def setUp(self):
        self.client = self.client_class()
        self.user = Usuario.objects.create_user(
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


class UserAdminViewsTests(TestCase):
    def setUp(self):
        # 1. Creamos un ADMIN
        self.admin_user = Usuario.objects.create_user(
            email="admin@test.com",
            username="admin@test.com",
            password="password123",
            role="admin",
            first_name="Admin",
            last_name="Jefe",
        )

        # 2. Creamos un USUARIO NORMAL (Cliente)
        self.normal_user = Usuario.objects.create_user(
            email="user@test.com",
            username="user@test.com",
            password="password123",
            role="user",
            first_name="Cliente",
            last_name="Uno",
        )

        # 3. Creamos un USUARIO OBJETIVO (Para editar/borrar)
        self.target_user = Usuario.objects.create_user(
            email="target@test.com",
            username="target@test.com",
            password="password123",
            role="user",
            first_name="Zacarias",
            last_name="Target",
        )

        # URLs
        self.url_list = reverse("user_list")
        self.url_create = reverse("user_create_admin")
        self.url_edit = reverse("user_edit_admin", args=[self.target_user.pk])
        self.url_delete = reverse("user_delete_admin", args=[self.target_user.pk])
        self.url_dashboard = reverse("dashboard")
        self.url_login = reverse("login")

    # ========================================================
    # 1. PRUEBAS DE SEGURIDAD
    # ========================================================

    def test_anon_user_redirects_to_login(self):
        """Si no estás logueado, no entras."""
        endpoints = [self.url_list, self.url_create, self.url_edit, self.url_delete]
        for url in endpoints:
            resp = self.client.get(url)
            # Redirige al login (302)
            self.assertNotEqual(resp.status_code, 200)

    def test_normal_user_redirects_to_dashboard(self):
        """Si eres cliente, te echa al dashboard."""
        self.client.force_login(self.normal_user)
        endpoints = [self.url_list, self.url_create, self.url_edit, self.url_delete]
        for url in endpoints:
            resp = self.client.get(url)
            self.assertRedirects(resp, self.url_dashboard)

    def test_admin_can_access(self):
        """El admin entra hasta la cocina."""
        self.client.force_login(self.admin_user)
        resp = self.client.get(self.url_list)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "user/user_list.html")

    # ========================================================
    # 2. PRUEBAS DE LISTADO (Filtros y Orden)
    # ========================================================

    def test_list_filter_role(self):
        self.client.force_login(self.admin_user)
        # Filtramos solo admins
        resp = self.client.get(self.url_list, {"role": "admin"})
        users = resp.context["users"]
        self.assertIn(self.admin_user, users)
        self.assertNotIn(self.normal_user, users)

    def test_list_order_by_name(self):
        self.client.force_login(self.admin_user)
        # Orden A-Z: 'Admin' va antes que 'Zacarias'
        resp = self.client.get(self.url_list, {"order": "name_asc"})
        users = list(resp.context["users"])

        # Verificamos posiciones relativas
        index_admin = users.index(self.admin_user)
        index_target = users.index(self.target_user)
        self.assertTrue(index_admin < index_target)

    # ========================================================
    # 3. PRUEBA DE CREAR (Sin foto)
    # ========================================================

    def test_create_user_success(self):
        self.client.force_login(self.admin_user)

        # Datos sin archivo de imagen
        data = {
            "email": "new@test.com",
            "first_name": "Nuevo",
            "last_name": "Usuario",
            "role": "user",
            "is_active": True,
            "password1": "Pass12345",  # Campos requeridos por tu AdminUserCreationForm
            "password2": "Pass12345",
        }

        resp = self.client.post(self.url_create, data)

        # Debe redirigir al listado
        self.assertRedirects(resp, self.url_list)

        # Verificamos que existe en DB
        self.assertTrue(Usuario.objects.filter(email="new@test.com").exists())

        # Verificamos que NO nos ha logueado con el nuevo usuario (el admin sigue siendo admin)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.admin_user.pk)

    # ========================================================
    # 4. PRUEBA DE EDITAR (Sin foto)
    # ========================================================

    def test_update_user_success(self):
        self.client.force_login(self.admin_user)

        data = {
            "email": "updated@test.com",  # Cambiamos email
            "first_name": "Editado",
            "last_name": "Test",
            "role": "admin",  # Lo ascendemos a admin
            "is_active": False,  # Lo baneamos
        }

        resp = self.client.post(self.url_edit, data)

        self.assertRedirects(resp, self.url_list)

        # Refrescamos desde DB para comprobar cambios
        self.target_user.refresh_from_db()
        self.assertEqual(self.target_user.email, "updated@test.com")
        self.assertEqual(self.target_user.role, "admin")
        self.assertFalse(self.target_user.is_active)

    # ========================================================
    # 5. PRUEBAS DE BORRAR
    # ========================================================

    def test_delete_user_success(self):
        self.client.force_login(self.admin_user)

        # 1. GET muestra confirmación
        resp_get = self.client.get(self.url_delete)
        self.assertEqual(resp_get.status_code, 200)
        self.assertTemplateUsed(resp_get, "user/confirm_delete_user_admin.html")

        # 2. POST borra
        resp_post = self.client.post(self.url_delete)
        self.assertRedirects(resp_post, self.url_list)

        # Verificamos que murió
        self.assertFalse(Usuario.objects.filter(pk=self.target_user.pk).exists())

    def test_admin_cannot_delete_self(self):
        """El admin no puede borrarse a sí mismo."""
        self.client.force_login(self.admin_user)

        url_delete_self = reverse("user_delete_admin", args=[self.admin_user.pk])

        # Intentamos borrar al admin logueado -> Debe redirigir al listado sin borrar
        resp = self.client.post(url_delete_self)
        self.assertRedirects(resp, self.url_list)

        # Verificamos que sigue vivo
        self.assertTrue(Usuario.objects.filter(pk=self.admin_user.pk).exists())
