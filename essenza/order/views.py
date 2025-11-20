import stripe
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db.models import F
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

# Importaciones de tus modelos
from product.models import Product

from .models import Order, OrderProduct, Status

# Configuración de Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


# --------------------------------------------------------------------
# 1. FUNCIÓN AUXILIAR NECESARIA
# --------------------------------------------------------------------
def get_or_create_cart(request):
    """
    Obtiene la Order más reciente con status='PENDING' (asumida como carrito)
    o crea una nueva Order en estado 'PENDING'. Solo para usuarios logueados.
    """
    # Deny access to admin/staff users explicitly
    if request.user.is_authenticated and (
        getattr(request.user, "role", None) == "admin"
        or getattr(request.user, "is_staff", False)
    ):
        raise PermissionDenied(
            "Acceso denegado: administradores no pueden usar el carrito."
        )

    if request.user.is_authenticated:
        try:
            cart = (
                Order.objects.filter(user=request.user, status=Status.PENDING)
                .order_by("-placed_at")
                .first()
            )

            if cart is None:
                raise ObjectDoesNotExist

        except ObjectDoesNotExist:
            cart = Order.objects.create(
                user=request.user,
                status=Status.PENDING,
                address="",
            )
        return cart
    else:
        return None


# --------------------------------------------------------------------
# 2. VISTAS DEL CARRITO (TUS CLASES EXISTENTES)
# --------------------------------------------------------------------


class CartDetailView(View):
    template_name = "order/cart_detail.html"

    def get(self, request):
        cart = None
        if request.user.is_authenticated:
            cart = get_or_create_cart(request)
            cart_items = cart.order_products.all()
            cart_total = (
                sum(item.product.price * item.quantity for item in cart_items)
                if cart_items
                else 0
            )
        else:
            cart_session = request.session.get("cart_session", {})
            cart_items = []
            cart_total = 0

            if cart_session:
                product_pks = [int(pk) for pk in cart_session.keys()]
                products = Product.objects.filter(pk__in=product_pks)

                for product in products:
                    pk_str = str(product.pk)
                    quantity = cart_session[pk_str]["quantity"]
                    cart_items.append(
                        {
                            "product": product,
                            "quantity": quantity,
                            "subtotal": quantity * product.price,
                            "pk": product.pk,
                        }
                    )
                    cart_total = sum(
                        item["product"].price * item["quantity"] for item in cart_items
                    )

        context = {
            "cart": cart,
            "cart_items": cart_items,
            "cart_total": cart_total,
        }
        return render(request, self.template_name, context)


class AddToCartView(View):
    def post(self, request, product_pk):
        product = get_object_or_404(Product, pk=product_pk)

        try:
            quantity = int(request.POST.get("quantity", 1))
            if quantity < 1:
                quantity = 1
        except ValueError:
            quantity = 1

        cart = get_or_create_cart(request)

        if cart:
            # LOGUEADO
            cart_item = cart.order_products.filter(product=product).first()
            if cart_item:
                cart_item.quantity = F("quantity") + quantity
                cart_item.save(update_fields=["quantity"])
                cart_item.refresh_from_db()
                messages.success(
                    request,
                    f"Se ha añadido {quantity} unidad(es) de '{product.name}'.",
                )
            else:
                OrderProduct.objects.create(
                    order=cart, product=product, quantity=quantity
                )
                messages.success(request, f"'{product.name}' se ha añadido al carrito.")
        else:
            # ANÓNIMO (SESIÓN)
            cart_session = request.session.get("cart_session", {})
            product_pk_str = str(product_pk)

            if product_pk_str in cart_session:
                cart_session[product_pk_str]["quantity"] += quantity
                messages.success(
                    request,
                    f"Se ha añadido {quantity} unidad(es) de '{product.name}'.",
                )
            else:
                cart_session[product_pk_str] = {
                    "quantity": quantity,
                    "price": str(product.price),
                }
                messages.success(request, f"'{product.name}' se ha añadido al carrito.")

            request.session["cart_session"] = cart_session
            request.session.modified = True

        return redirect("cart_detail")


class UpdateCartSessionView(View):
    def post(self, request, product_pk):
        if request.user.is_authenticated:
            return redirect("cart_detail")

        cart_session = request.session.get("cart_session", {})
        product_pk_str = str(product_pk)
        product = get_object_or_404(Product, pk=product_pk)

        try:
            new_quantity = int(request.POST.get("quantity", 0))
        except ValueError:
            new_quantity = -1

        if product_pk_str in cart_session:
            if new_quantity <= 0:
                del cart_session[product_pk_str]
                messages.info(request, f"'{product.name}' eliminado.")
            else:
                if new_quantity > product.stock:
                    new_quantity = product.stock
                    messages.warning(request, f"Stock limitado a {product.stock}.")

                cart_session[product_pk_str]["quantity"] = new_quantity
                messages.success(request, "Cantidad actualizada.")

            request.session["cart_session"] = cart_session
            request.session.modified = True

        return redirect("cart_detail")


class UpdateCartItemView(View):
    def post(self, request, item_pk):
        cart_item = get_object_or_404(OrderProduct, pk=item_pk)
        cart = get_or_create_cart(request)

        if cart_item.order.pk != cart.pk:
            return redirect("cart_detail")

        try:
            new_quantity = int(request.POST.get("quantity", 0))
        except ValueError:
            new_quantity = -1

        if new_quantity <= 0:
            cart_item.delete()
            messages.info(request, "Producto eliminado.")
        else:
            cart_item.quantity = new_quantity
            cart_item.save(update_fields=["quantity"])
            messages.success(request, "Cantidad actualizada.")

        return redirect("cart_detail")


# --------------------------------------------------------------------
# 3. VISTAS DE STRIPE (Integración Final con tus Modelos)
# --------------------------------------------------------------------


def create_checkout(request):
    """
    Crea la sesión de pago. Calcula el precio total real basándose en
    si el usuario es logueado (DB) o anónimo (Session).
    """
    domain_url = settings.DOMAIN_URL
    total_amount = 0

    # --- 1. Calcular el total REAL ---
    if request.user.is_authenticated:
        # A. Usuario Logueado: Usamos la Order de la DB
        cart = get_or_create_cart(request)
        cart_items = cart.order_products.all()

        if not cart_items:
            messages.error(request, "Tu carrito está vacío.")
            return redirect("cart_detail")

        for item in cart_items:
            total_amount += item.product.price * item.quantity

    else:
        # B. Usuario Anónimo: Usamos la Sesión
        cart_session = request.session.get("cart_session", {})

        if not cart_session:
            messages.error(request, "Tu carrito está vacío.")
            return redirect("cart_detail")

        # Recuperamos precios reales de la DB para evitar fraudes
        product_pks = [int(pk) for pk in cart_session.keys()]
        products = Product.objects.filter(pk__in=product_pks)

        for product in products:
            pk_str = str(product.pk)
            qty = cart_session[pk_str]["quantity"]
            total_amount += product.price * qty

    # --- 2. Crear Sesión de Stripe ---
    try:
        # Convertir a céntimos (Stripe trabaja con enteros: 10.00€ -> 1000)
        amount_in_cents = int(total_amount * 100)

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "eur",
                        "unit_amount": amount_in_cents,
                        "product_data": {
                            "name": "Pedido Essenza",
                            "description": "Compra",
                        },
                    },
                    "quantity": 1,
                },
            ],
            mode="payment",
            success_url=domain_url + "/order/success/?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=domain_url + "/order/cancelled/",
        )
        return redirect(checkout_session.url, code=303)

    except Exception as e:
        return HttpResponse(f"Error al conectar con Stripe: {e}")


def successful_payment(request):
    """
    Verifica con Stripe que el pago sea real.
    Si es correcto, actualiza el estado a PAID (Logueado) o limpia sesión (Anónimo).
    """
    session_id = request.GET.get("session_id")

    if not session_id:
        return HttpResponse("Error: No se ha recibido confirmación de pago.")

    try:
        # Preguntar a Stripe directamente
        session = stripe.checkout.Session.retrieve(session_id)

        if session.payment_status == "paid":
            # --- PAGO CONFIRMADO ---

            if request.user.is_authenticated:
                # 1. Usuario Logueado: Actualizar DB
                cart = get_or_create_cart(request)

                # ACTUALIZACIÓN CORRECTA SEGÚN TUS MODELOS:
                cart.status = Status.PAID
                cart.save()

                print(f"✅ Orden {cart.id} pagada y actualizada a PAID.")

            else:
                # 2. Usuario Anónimo: Limpiar Sesión
                request.session["cart_session"] = {}
                request.session.modified = True
                print("✅ Pago anónimo verificado. Sesión limpiada.")

            # Renderizar página de gracias
            return render(request, "order/success.html")

        else:
            return HttpResponse("El pago no se ha completado.")

    except Exception as e:
        return HttpResponse(f"Error verificando el pago: {e}")


def cancelled_payment(request):
    return render(request, "order/cancel.html")
