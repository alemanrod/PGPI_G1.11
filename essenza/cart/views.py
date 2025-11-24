from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from product.models import Product

from .models import Cart, CartProduct


class CartDetailView(View):
    """
    Muestra el carrito.
    - Si es usuario logueado: Lee de la base de datos
    - Si es anónimo: Lee de la sesión
    """

    template_name = "cart/cart_detail.html"

    def get(self, request):
        context = {"cart_products": [], "total_price": 0}

        # Si esta logueado
        if request.user.is_authenticated:
            # Busca un carrito exitente y si no lo hay, lo crea nuevo
            try:
                cart = get_object_or_404(Cart, user=request.user)
                # Cogemos los datos del carrito desde la base de datos
                context["cart_products"] = cart.cart_products.all()
                context["total_price"] = cart.total_price
                context["cart"] = cart
            except Exception:
                pass

        # Si no está logueado, usamos la sesión
        else:
            cart_session = request.session.get("cart_session", {})
            cart_products = []
            total_price = 0

            if cart_session:
                # Obtenemos los productos
                product_ids = [int(pk) for pk in cart_session.keys()]
                products = Product.objects.filter(pk__in=product_ids)

                # Construimos los items del carrito
                for product in products:
                    quantity = cart_session[str(product.pk)]["quantity"]
                    subtotal = quantity * product.price

                    # Añadimos al listado de items del carrito la info necesaria
                    cart_products.append(
                        {
                            "product": product,
                            "quantity": quantity,
                            "subtotal": subtotal,
                            "pk": product.pk,
                        }
                    )
                    total_price += subtotal

            context["cart_products"] = cart_products
            context["total_price"] = total_price

        return render(request, self.template_name, context)


class AddToCartView(View):
    """
    Añade productos al carrito (DB o Sesión).
    """

    def post(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id)

        if product.stock <= 0:
            return redirect("catalog")

        try:
            quantity = int(request.POST.get("quantity", 1))
            if quantity < 1:
                quantity = 1
        except ValueError:
            quantity = 1

        # Si el usuario está logueado
        if request.user.is_authenticated:
            cart, create = Cart.objects.get_or_create(user=request.user)

            if cart:
                cart_product, created = CartProduct.objects.get_or_create(
                    cart=cart, product=product, defaults={"quantity": quantity}
                )
            else:
                cart_product, created = CartProduct.objects.get_or_create(
                    cart=create, product=product, defaults={"quantity": quantity}
                )

            if not created:
                if cart_product.quantity + quantity > product.stock:
                    cart_product.quantity = product.stock
                    return redirect("cart_detail")
                else:
                    cart_product.quantity += quantity
                cart_product.save()

        # Si el usuario no está logueado, guardamos en sesión
        else:
            cart_session = request.session.get("cart_session", {})
            product_id_str = str(product_id)

            if product_id_str in cart_session:
                if cart_session[product_id_str]["quantity"] + quantity > product.stock:
                    cart_session[product_id_str]["quantity"] = product.stock
                    return redirect("cart_detail")
                else:
                    cart_session[product_id_str]["quantity"] += quantity
            else:
                cart_session[product_id_str] = {
                    "quantity": quantity,
                    "price": str(product.price),
                }

            request.session["cart_session"] = cart_session
            request.session.modified = True

        return redirect("cart_detail")


class RemoveFromCartView(View):
    """
    Elimina productos del carrito.
    """

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


class UpdateCartItemView(View):
    """
    Actualiza la cantidad de un producto.
    """

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
