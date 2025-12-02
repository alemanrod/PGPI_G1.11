import stripe
from cart.models import Cart
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
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
class OrderHistoryView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = "order/order_history.html"

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == "user"

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect("login")
        return redirect("stock")

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
class OrderSearchView(UserPassesTestMixin, View):
    template_name = "order/order_search.html"

    def test_func(self):
        return (
            not self.request.user.is_authenticated or self.request.user.role == "user"
        )

    def handle_no_permission(self):
        return redirect("stock")

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
class OrderUpdateStatusView(LoginRequiredMixin, UserPassesTestMixin, View):
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


def _process_order(request, user, email, address, is_paid):
    """
    Función auxiliar interna para procesar el pedido.
    Se usa tanto para el retorno de Stripe como para Contrarreembolso.
    """
    items_to_process = []
    cart_to_delete = None

    # 1. Obtener items (Lógica unificada para Auth/Anon)
    if user:  # Usuario autenticado
        cart = Cart.objects.filter(user=user).first()
        if cart:
            cart_to_delete = cart
            for cart_item in cart.cart_products.select_related("product").all():
                items_to_process.append(
                    {
                        "product": cart_item.product,
                        "quantity": cart_item.quantity,
                    }
                )
    else:  # Usuario anónimo (Sesión)
        cart_session = request.session.get("cart_session", {})
        if cart_session:
            product_pks = [int(pk) for pk in cart_session.keys()]
            products = Product.objects.filter(pk__in=product_pks)
            for product in products:
                qty = cart_session[str(product.pk)]["quantity"]
                items_to_process.append({"product": product, "quantity": qty})

    if not items_to_process:
        return None  # Carrito vacío o error

    # 2. Buscar usuario registrado para asociar (si existe por email)
    User = get_user_model()
    user_for_order = user if user else User.objects.filter(email=email).first()

    # 3. Crear el Pedido
    new_order = Order.objects.create(
        user=user_for_order,
        email=email,
        address=address,
        status=Status.EN_PREPARACION,
        is_paid=is_paid,
    )

    # 4. Crear OrderProducts y actualizar Stock
    for item_data in items_to_process:
        product = item_data["product"]
        qty = item_data["quantity"]

        OrderProduct.objects.create(order=new_order, product=product, quantity=qty)
        # Actualizamos stock de forma segura
        Product.objects.filter(pk=product.pk).update(stock=F("stock") - qty)

    # 5. Borrar el carrito
    if cart_to_delete:
        cart_to_delete.delete()
    else:
        request.session["cart_session"] = {}
        request.session.modified = True

    # 6. Enviar Email (Lógica común)
    try:
        tracking_url = request.build_absolute_uri(
            reverse("order_tracking", args=[new_order.tracking_code])
        )
        payment_msg = (
            "Pagado con Tarjeta" if is_paid else "Pendiente de pago (Contrarreembolso)"
        )

        subject = f"Confirmación de Pedido #{new_order.tracking_code} - Essenza"
        message = f"""
        Hola!
        Gracias por tu compra en Essenza.
        
        Detalles del pedido:
        Localizador: {new_order.tracking_code}
        Total: {new_order.total:.2f} €
        Estado del pago: {payment_msg}
        Dirección: {new_order.address}

        Sigue tu pedido aquí: {tracking_url}
        """
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [new_order.email],
            fail_silently=True,
        )
    except Exception as e:
        print(f"Error enviando email: {e}")

    return new_order


def create_checkout(request):
    """
    Maneja el inicio del proceso de pago.
    """
    if request.method != "POST":
        return redirect("cart_detail")

    payment_method = request.POST.get("payment_method")  # 'stripe' o 'cod'

    # --- OPCIÓN A: CONTRARREMBOLSO (COD) ---
    if payment_method == "cod":
        # 1. Capturamos los datos DEL FORMULARIO HTML
        name = request.POST.get("shipping_name")
        email_input = request.POST.get("shipping_email")
        address = request.POST.get("shipping_address")
        city = request.POST.get("shipping_city")
        zip_code = request.POST.get("shipping_zip")

        # 2. Validación básica (si falta algo, detenemos todo)
        if not (name and email_input and address and city and zip_code):
            return HttpResponse(
                "Error: Faltan datos de envío obligatorios.", status=400
            )

        # 3. Construimos la dirección completa en un solo string
        full_address = f"{address}, {city} ({zip_code})"

        # 4. Determinamos el usuario y email
        user = request.user if request.user.is_authenticated else None

        # Prioridad: Si el usuario escribió un email en el form, usamos ese.
        final_email = email_input if email_input else user.email

        if not final_email:
            return HttpResponse("Error: Se requiere un email válido.", status=400)

        # 5. Procesamos el pedido
        with transaction.atomic():
            order = _process_order(
                request,
                user=user,
                email=final_email,
                address=full_address,
                is_paid=False,  # COD = No pagado aún
            )

        if order:
            # IMPORTANTE: Redirigimos pasando el ID del pedido para mostrar éxito
            return render(request, "order/success.html", {"order": order})
        else:
            return redirect("cart_detail")

    # --- OPCIÓN B: STRIPE ---
    elif payment_method == "stripe":
        # --- Lógica de Items para Stripe ---
        cart_items_temp = []
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
            if not cart:
                return redirect("cart_detail")  # Seguridad extra
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
            products = Product.objects.filter(
                pk__in=[int(k) for k in cart_session.keys()]
            )
            for p in products:
                cart_items_temp.append(
                    {
                        "product": p,
                        "quantity": cart_session[str(p.pk)]["quantity"],
                        "price": p.price,
                    }
                )

        line_items_stripe = []
        for item in cart_items_temp:
            line_items_stripe.append(
                {
                    "price_data": {
                        "currency": "eur",
                        "unit_amount": int(item["price"] * 100),
                        "product_data": {"name": item["product"].name},
                    },
                    "quantity": item["quantity"],
                }
            )

        # --- Lógica de Envío ---

        domain_url = settings.DOMAIN_URL
        try:
            customer_email = (
                request.user.email if request.user.is_authenticated else None
            )

            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=line_items_stripe,
                mode="payment",
                shipping_address_collection={"allowed_countries": ["ES"]},
                customer_email=customer_email,
                success_url=domain_url
                + "/order/success/?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=domain_url + "/order/cancelled/",
            )
            return redirect(checkout_session.url, code=303)

        except Exception as e:
            return HttpResponse(f"Error al conectar con Stripe: {e}")

    return redirect("cart_detail")


def successful_payment(request):
    """
    Retorno de Stripe.
    """
    session_id = request.GET.get("session_id")
    if not session_id:
        return HttpResponse("Error: No session ID")

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == "paid":
            # Extraer datos de Stripe
            stripe_email = session.customer_details.email
            address_data = session.customer_details.address
            shipping_address = (
                f"{address_data.line1}, {address_data.city}, {address_data.postal_code}"
            )

            user = request.user if request.user.is_authenticated else None

            with transaction.atomic():
                # Llamamos a la función común
                new_order = _process_order(
                    request,
                    user=user,
                    email=stripe_email,
                    address=shipping_address,
                    is_paid=True,  # <--- STRIPE = TRUE
                )

            return render(request, "order/success.html", {"order": new_order})
        else:
            return render(request, "order/cancel.html")
    except Exception as e:
        return HttpResponse(f"Error: {e}")


def cancelled_payment(request):
    return render(request, "order/cancel.html")
