import stripe
from cart.models import Cart
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from product.models import Product

# Configuración de Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


# --------------------------------------------------------------------
# VISTAS DE STRIPE
# --------------------------------------------------------------------


def create_checkout(request):
    """
    Crea la sesión de pago. Calcula el precio total real basándose en
    si el usuario es logueado (DB) o anónimo (Session).
    """
    domain_url = settings.DOMAIN_URL
    total_amount = 0

    # --- 1. Calcular el total ---
    if request.user.is_authenticated:
        # A. Usuario Logueado: Usamos la Order de la DB
        cart = get_object_or_404(Cart, user=request.user)
        total_amount = cart.total_price

    else:
        # B. Usuario Anónimo: Usamos la Sesión
        cart_session = request.session.get("cart_session", {})

        if not cart_session:
            messages.error(request, "Tu carrito está vacío.")
            return redirect("cart_detail")

        # Recuperamos precios reales de la DB
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
                            "description": "Compra en Essenza",
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
    Si es correcto, actualiza el estado a EN_PREPARACION (Logueado) o limpia sesión (Anónimo).
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
                cart = get_object_or_404(Cart, user=request.user)
                cart.delete()  # Limpiar carrito tras pago

                # AQUI HAY QUE AÑADIR LA LÓGICA DE CREACIÓN DE ORDER

                print("✅ Order 'order.id' pagada y actualizada a EN_PREPARACION.")

            else:
                # 2. Usuario Anónimo: Limpiar Sesión
                request.session["cart_session"] = {}
                request.session.modified = True

                # AQUI HAY QUE AÑADIR LA LÓGICA DE CREACIÓN DE ORDER

                print("✅ Pago anónimo verificado. Sesión limpiada.")

            # Renderizar página de gracias
            return render(request, "order/success.html")

        else:
            return HttpResponse("El pago no se ha completado.")

    except Exception as e:
        return HttpResponse(f"Error verificando el pago: {e}")


def cancelled_payment(request):
    return render(request, "order/cancel.html")
