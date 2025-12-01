from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from product.models import Product

from .models import Cart, CartProduct


class CartDetailView(UserPassesTestMixin, View):
    """
    Muestra el carrito (si no eres admin).
    - Si es usuario logueado: Lee de la base de datos
    - Si es anónimo: Lee de la sesión
    """

    def test_func(self):
        return (
            not self.request.user.is_authenticated or self.request.user.role == "user"
        )

    def handle_no_permission(self):
        return redirect("stock")

    template_name = "cart/cart_detail.html"

    def get(self, request):
        context = {"cart_products": [], "shipping": 0, "subtotal": 0, "total": 0}

        # Si esta logueado
        if request.user.is_authenticated:
            # Busca un carrito exitente y si no lo hay, lo crea nuevo
            try:
                cart = get_object_or_404(Cart, user=request.user)
                # Cogemos los datos del carrito desde la base de datos
                context["cart_products"] = cart.cart_products.all()
                context["shipping"] = cart.shipping
                context["subtotal"] = cart.subtotal
                context["total"] = cart.total
                context["cart"] = cart
            except Exception:
                pass

        # Si no está logueado, usamos la sesión
        else:
            cart_session = request.session.get("cart_session", {})
            cart_products = []
            subtotal = 0

            if cart_session:
                # Obtenemos los productos
                product_ids = [int(pk) for pk in cart_session.keys()]
                products = Product.objects.filter(pk__in=product_ids)

                # Construimos los items del carrito
                for product in products:
                    quantity = cart_session[str(product.pk)]["quantity"]
                    product_subtotal = quantity * product.price

                    # Añadimos al listado de items del carrito la info necesaria
                    cart_products.append(
                        {
                            "product": product,
                            "quantity": quantity,
                            "subtotal": product_subtotal,
                            "pk": product.pk,
                        }
                    )
                    subtotal += product_subtotal

            context["cart_products"] = cart_products
            context["subtotal"] = subtotal
            context["shipping"] = Decimal(4.99 if subtotal < 100 else 0)
            context["total"] = subtotal + context["shipping"]

        return render(request, self.template_name, context)


class AddToCartView(UserPassesTestMixin, View):
    """
    Añade productos al carrito.
    - Acción 'add': Se queda en la página y muestra mensaje.
    - Acción 'buy': Redirige al carrito.
    """

    def test_func(self):
        return (
            not self.request.user.is_authenticated or self.request.user.role == "user"
        )

    def handle_no_permission(self):
        return redirect("stock")

    def post(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id)

        # Guardar la URL anterior para volver si es "Añadir"
        next_url = request.META.get("HTTP_REFERER", "catalog")

        if product.stock <= 0:
            messages.error(request, "Este producto está agotado.")
            return redirect(next_url)

        try:
            quantity = int(request.POST.get("quantity", 1))
            if quantity < 1:
                quantity = 1
        except ValueError:
            quantity = 1

        # --- LÓGICA DE AÑADIR (unificada) ---
        if request.user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(user=request.user)
            # Usamos get_or_create con defaults para evitar condiciones de carrera simples
            cart_product, created = CartProduct.objects.get_or_create(
                cart=cart, product=product, defaults={"quantity": 0}
            )

            # Si se acaba de crear, quantity es 0 (por el default), si ya existía tiene X
            # Así que simplemente sumamos la cantidad nueva.
            if created:
                cart_product.quantity = quantity
            else:
                cart_product.quantity += quantity

            # Validación Stock
            if cart_product.quantity > product.stock:
                cart_product.quantity = product.stock
                messages.warning(
                    request, f"Has alcanzado el límite de stock ({product.stock})."
                )

            cart_product.save()

        else:
            # Lógica de Sesión
            cart_session = request.session.get("cart_session", {})
            product_id_str = str(product_id)

            if product_id_str in cart_session:
                current_qty = cart_session[product_id_str]["quantity"]
                if current_qty + quantity > product.stock:
                    cart_session[product_id_str]["quantity"] = product.stock
                    messages.warning(request, "Has alcanzado el límite de stock.")
                else:
                    cart_session[product_id_str]["quantity"] += quantity
            else:
                cart_session[product_id_str] = {
                    "quantity": quantity,
                    "price": str(product.price),
                }

            request.session["cart_session"] = cart_session
            request.session.modified = True

        # --- AQUÍ ESTÁ LA MAGIA DE LA REDIRECCIÓN ---
        action = request.POST.get("action", "add")  # 'add' o 'buy'

        if action == "buy":
            # Si quiere comprar ya, lo llevamos al carrito
            return redirect("cart_detail")
        else:
            # Si solo añade, le damos feedback y lo dejamos donde estaba
            messages.success(request, f"¡{product.name} añadido al carrito!")
            return redirect(next_url)


class RemoveFromCartView(UserPassesTestMixin, View):
    """
    Elimina productos del carrito.
    """

    def test_func(self):
        return (
            not self.request.user.is_authenticated or self.request.user.role == "user"
        )

    def handle_no_permission(self):
        return redirect("stock")

    def post(self, request, product_id):
        # Si el usuario está logueado
        if request.user.is_authenticated:
            cart = get_object_or_404(Cart, user=request.user)
            # Buscamos el CartProduct que coincida con el usuario y el producto
            cart_product = get_object_or_404(
                CartProduct,
                cart=cart,
                pk=product_id,
            )
            cart_product.delete()
            if not cart.cart_products.exists():
                cart.delete()

        # Si el usuario no está logueado, eliminamos de la sesión
        else:
            cart_session = request.session.get("cart_session", {})
            product_id_str = str(product_id)

            if product_id_str in cart_session:
                del cart_session[product_id_str]
                request.session["cart_session"] = cart_session
                request.session.modified = True

        return redirect("cart_detail")


class UpdateCartItemView(UserPassesTestMixin, View):
    """
    Actualiza la cantidad de un producto.
    """

    def test_func(self):
        return (
            not self.request.user.is_authenticated or self.request.user.role == "user"
        )

    def handle_no_permission(self):
        return redirect("stock")

    def post(self, request, product_id):
        try:
            new_quantity = int(request.POST.get("quantity", 1))
        except ValueError:
            new_quantity = 1

        # Si la cantidad es 0 o negativa, eliminamos el producto
        if new_quantity <= 0:
            return RemoveFromCartView().post(request, product_id)

        # Si el usuario está logueado
        if request.user.is_authenticated:
            cart_product = get_object_or_404(
                CartProduct,
                cart=get_object_or_404(Cart, user=request.user),
                pk=product_id,
            )
            cart_product.quantity = new_quantity
            cart_product.save()

        # Si el usuario no está logueado, actualizamos en la sesión
        else:
            cart_session = request.session.get("cart_session", {})
            product_id_str = str(product_id)

            if product_id_str in cart_session:
                cart_session[product_id_str]["quantity"] = new_quantity
                request.session["cart_session"] = cart_session
                request.session.modified = True

        return redirect("cart_detail")
