import stripe
from cart.models import Cart
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db import transaction  # Para la integridad de datos
from django.db.models import (
    F,  # Para restar el stock de forma segura
    Prefetch,
    Q,
)
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from product.models import Product

from .models import Order, OrderProduct, Status

# Configuración de Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


# =======================================================
# LISTADO DE PEDIDOS - ADMIN
# =======================================================
class OrderListAdminView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = "order/order_list_admin.html"

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == "admin"

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect("login")
        return redirect("dashboard")

    def get(self, request):
        orders = (
            Order.objects.select_related("user")
            .prefetch_related(
                Prefetch(
                    "order_products",
                    queryset=OrderProduct.objects.select_related("product"),
                )
            )
            .order_by("-placed_at")
        )
        # 2. Lógica de Filtrado
        status_filter = request.GET.get("status")

        # Validamos que el estado sea real para evitar errores
        valid_statuses = [
            s[0] for s in Status.choices
        ]  # ['en_preparacion', 'enviado', 'entregado']

        if status_filter in valid_statuses:
            orders = orders.filter(status=status_filter)
        return render(request, self.template_name, {"orders": orders})


# =======================================================
# LISTADO DE PEDIDOS - USER
# =======================================================
class OrderHistoryView(LoginRequiredMixin, View):
    template_name = "order/order_history.html"

    def get(self, request):
        # CORRECCIÓN 1: Usamos Q para buscar por Usuario O por Email
        # Esto permite ver pedidos hechos como invitado si el email coincide
        orders = (
            Order.objects.filter(Q(user=request.user) | Q(email=request.user.email))
            # CORRECCIÓN 2: Eliminado .exclude(status=Status.EN_PREPARACION)
            # Ahora los pedidos 'en preparación' (recién pagados) SÍ se muestran.
            .prefetch_related(
                Prefetch(
                    "order_products",
                    queryset=OrderProduct.objects.select_related("product"),
                )
            )
            .order_by("-placed_at")
            .distinct()  # Evita duplicados si user y email coinciden en el mismo pedido
        )
        return render(request, self.template_name, {"orders": orders})


# =======================================================
# BUSQUEDA DE PEDIDO
# =======================================================
class OrderSearchView(View):
    template_name = "order/order_search.html"

    def get(self, request):
        # Solo muestra el formulario vacío
        return render(request, self.template_name, {"searched": False})

    def post(self, request):
        order_tracking_code = request.POST.get("tracking_code", "").strip()
        email = request.POST.get("email", "").strip().lower()

        order = None
        error = None

        if not order_tracking_code or not email:
            error = "Debes introducir el número de pedido y el email."
        else:
            try:
                order = (
                    Order.objects.select_related("user")
                    .prefetch_related(
                        Prefetch(
                            "order_products",
                            queryset=OrderProduct.objects.select_related("product"),
                        )
                    )
                    .get(tracking_code=order_tracking_code, email__iexact=email)
                )
            except Order.DoesNotExist:
                error = "No se ha encontrado ningún pedido con esos datos."

        # Si encontramos el pedido, podemos redirigir a la vista de detalle bonita que ya tienes
        if order:
            return redirect("order_tracking", tracking_code=order_tracking_code)

        # Si hubo error, volvemos a mostrar el formulario con el mensaje
        messages.error(request, error)
        context = {
            "order": None,
            "searched": True,
            "tracking_code": order_tracking_code,
            "email": email,
        }
        return render(request, self.template_name, context)


# =======================================================
# SEGUIMIENTO ENVÍO
# =======================================================
class OrderTrackingView(View):
    def get(self, request, tracking_code):
        # Buscamos el pedido por su código único
        order = get_object_or_404(Order, tracking_code=tracking_code)
        return render(request, "order/tracking.html", {"order": order})


# =======================================================
# ACTUALIZAR ESTADO (SOLO ADMIN)
# =======================================================
class OrderUpdateStatusView(LoginRequiredMixin, View):
    """
    Permite a un administrador cambiar el estado de un pedido
    haciendo clic en la barra de progreso.
    """

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == "admin"

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect("login")
        return redirect("dashboard")

    def post(self, request, tracking_code):
        order = get_object_or_404(Order, tracking_code=tracking_code)
        new_status = request.POST.get("status")

        # Validamos que el estado sea uno de los permitidos
        valid_statuses = [choice[0] for choice in Status.choices]

        if new_status in valid_statuses:
            order.status = new_status
            order.save()

        # Redirigimos a la misma página de tracking para ver el cambio
        return redirect("order_tracking", tracking_code=order.tracking_code)


def create_checkout(request):
    """
    Crea la sesión de pago en Stripe y configura la recolección de dirección.
    Restringido: Los administradores NO pueden acceder aquí.
    """
    if request.user.is_authenticated and getattr(request.user, "role", None) == "admin":
        raise PermissionDenied("Los administradores no pueden realizar compras.")

    domain_url = settings.DOMAIN_URL
    cart_items_temp = []

    if request.user.is_authenticated:
        cart = get_object_or_404(Cart, user=request.user)
        for item in cart.cart_products.all():
            cart_items_temp.append(
                {
                    "product": item.product,
                    "quantity": item.quantity,
                    "price": item.product.price,
                }
            )
    else:
        cart_session = request.session.get("cart_session", {})
        if not cart_session:
            return redirect("cart_detail")

        product_pks = [int(pk) for pk in cart_session.keys()]
        products = Product.objects.filter(pk__in=product_pks)

        for product in products:
            qty = cart_session[str(product.pk)]["quantity"]
            cart_items_temp.append(
                {"product": product, "quantity": qty, "price": product.price}
            )

    line_items_stripe = []
    for item in cart_items_temp:
        amount_in_cents = int(item["price"] * 100)
        line_items_stripe.append(
            {
                "price_data": {
                    "currency": "eur",
                    "unit_amount": amount_in_cents,
                    "product_data": {
                        "name": item["product"].name,
                        "description": item["product"].description[:100]
                        if item["product"].description
                        else "Producto Essenza",
                    },
                },
                "quantity": item["quantity"],
            }
        )

    try:
        customer_email = request.user.email if request.user.is_authenticated else None

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=line_items_stripe,
            mode="payment",
            shipping_address_collection={
                "allowed_countries": ["ES"],
            },
            customer_email=customer_email,
            success_url=domain_url + "/order/success/?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=domain_url + "/order/cancelled/",
        )
        return redirect(checkout_session.url, code=303)

    except Exception as e:
        return HttpResponse(f"Error al conectar con Stripe: {e}")


def successful_payment(request):
    """
    Verifica el pago, crea el pedido y ACTUALIZA EL STOCK.
    Usa una transacción atómica para asegurar que todo se guarda o nada.
    """
    session_id = request.GET.get("session_id")

    if not session_id:
        return HttpResponse("Error: No se ha recibido confirmación de pago.")

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        customer_details = session.customer_details
        stripe_email = customer_details.email

        address_data = customer_details.address
        shipping_address = f"{address_data.line1}, {address_data.city}, {address_data.postal_code}, {address_data.country}"
        if address_data.line2:
            shipping_address += f", {address_data.line2}"

        if session.payment_status == "paid":
            # --- INICIO DE TRANSACCIÓN ---
            # Esto asegura que si falla la creación de productos, no se crea el pedido vacío
            with transaction.atomic():
                items_to_process = []
                cart_to_delete = None

                # Si esta logueado
                if request.user.is_authenticated:
                    cart = Cart.objects.filter(user=request.user).first()
                    if cart:
                        cart_to_delete = cart
                        for cart_item in cart.cart_products.select_related(
                            "product"
                        ).all():
                            items_to_process.append(
                                {
                                    "product": cart_item.product,
                                    "quantity": cart_item.quantity,
                                }
                            )
                # Si no esta logueado, usamos la sesion
                else:
                    cart_session = request.session.get("cart_session", {})
                    if cart_session:
                        product_pks = [int(pk) for pk in cart_session.keys()]
                        products = Product.objects.filter(pk__in=product_pks)
                        for product in products:
                            qty = cart_session[str(product.pk)]["quantity"]
                            items_to_process.append(
                                {"product": product, "quantity": qty}
                            )

                if not items_to_process:
                    # Si no hay productos, no creamos el pedido.
                    return HttpResponse(
                        "Error: No se encontraron productos en el carrito para procesar el pedido."
                    )

                # 3. Buscar usuario por email
                User = get_user_model()
                user_for_order = User.objects.filter(email=stripe_email).first()

                # 4. Crear el Pedido
                new_order = Order.objects.create(
                    user=user_for_order,  # Si no existe el usuario, se pone None
                    status=Status.EN_PREPARACION,
                    address=shipping_address,
                    email=stripe_email,
                )

                # 5. Crear OrderProducts y actualizamos el Stock
                for item_data in items_to_process:
                    product = item_data["product"]
                    qty = item_data["quantity"]

                    OrderProduct.objects.create(
                        order=new_order, product=product, quantity=qty
                    )

                    Product.objects.filter(pk=product.pk).update(stock=F("stock") - qty)

                # 6. Borrar el carrito
                if cart_to_delete:
                    cart_to_delete.delete()
                else:
                    request.session["cart_session"] = {}
                    request.session.modified = True
            # --- ENVÍO DE CORREO DE CONFIRMACIÓN ---
            try:
                # 1. Generar la URL absoluta de seguimiento
                tracking_url = request.build_absolute_uri(reverse("order_search"))

                # 2. Definir asunto y mensaje
                subject = f"Confirmación de Pedido #{new_order.tracking_code} - Essenza"

                # Mensaje simple en texto plano
                message = f"""
                Hola!

                Gracias por tu compra en Essenza.
                Tu pedido ha sido confirmado y se está preparando.

                Detalles del pedido:
                Nº de localizador: {new_order.tracking_code}
                Total: {new_order.total_price} €
                Dirección de envío: {new_order.address}

                Puedes seguir el estado de tu pedido aquí:
                {tracking_url}

                Gracias por confiar en nosotros.
                """

                # 3. Enviar el correo
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,  # Asegúrate de tener esto en settings.py
                    [new_order.email],  # El email del destinatario
                    fail_silently=True,  # Si falla, no rompe la web
                )
            except Exception as e:
                # Si falla el correo, lo imprimimos en consola pero dejamos pasar al usuario
                print(f"Error enviando email: {e}")

            return render(request, "order/success.html", {"order": new_order})

        else:
            return HttpResponse("El pago no se ha completado.")

    except Exception as e:
        return HttpResponse(f"Error verificando el pago o creando el pedido: {e}")


def cancelled_payment(request):
    return render(request, "order/cancel.html")
