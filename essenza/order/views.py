from django.shortcuts import get_object_or_404, redirect, render 
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import F # Importado para operaciones atómicas
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied

# Importaciones de tus modelos
from .models import Order, OrderProduct, Status
from product.models import Product 

# --------------------------------------------------------------------
# 1. FUNCIÓN AUXILIAR NECESARIA 
# --------------------------------------------------------------------
def get_or_create_cart(request): 
    """
    Obtiene la Order más reciente con status='PENDING' (asumida como carrito)
    o crea una nueva Order en estado 'PENDING'. Solo para usuarios logueados.
    """
    # Deny access to admin/staff users explicitly
    if request.user.is_authenticated and (getattr(request.user, 'role', None) == 'admin' or getattr(request.user, 'is_staff', False)):
        raise PermissionDenied("Acceso denegado: administradores no pueden usar el carrito.")

    if request.user.is_authenticated:
        # Lógica para usuarios logueados
        try:
            cart = Order.objects.filter(
                user=request.user, 
                status=Status.PENDING 
            ).order_by('-placed_at').first()
            
            if cart is None:
                raise ObjectDoesNotExist

        except ObjectDoesNotExist:
            cart = Order.objects.create(
                user=request.user, 
                status=Status.PENDING,
                address="",  # Provide an empty string to avoid IntegrityError
            )
            
        return cart
    else:
        # Los anónimos usan la sesión
        return None

# --------------------------------------------------------------------
# 2. VISTAS
# --------------------------------------------------------------------

# order/views.py (Fragmento de CartDetailView)

class CartDetailView(View):
    """Muestra el contenido del carrito activo del usuario (DB) o de la sesión (Anónimo)."""
    template_name = 'order/cart_detail.html'
    
    def get(self, request):
        cart = None
        if request.user.is_authenticated:
            # LÓGICA 1: Usuario logueado (lee de la DB)
            cart = get_or_create_cart(request)
            cart_items = cart.order_products.all()
            cart_total = sum(item.product.price * item.quantity for item in cart_items) if cart_items else 0
        else:
            # LÓGICA 2: Usuario anónimo (lee de la Sesión)
            cart_session = request.session.get('cart_session', {})
            cart_items = []
            cart_total = 0
            
            # Si hay ítems en la sesión, construimos una lista para la plantilla
            if cart_session:
                product_pks = [int(pk) for pk in cart_session.keys()]
                
                # Buscamos todos los objetos Product de la DB de una vez
                products = Product.objects.filter(pk__in=product_pks)
                
                # Iteramos sobre los productos para crear la lista de ítems del carrito
                for product in products:
                    pk_str = str(product.pk)
                    quantity = cart_session[pk_str]['quantity']
                    
                    # Creamos un objeto temporal para pasarlo al template
                    cart_items.append({
                        'product': product,
                        'quantity': quantity,
                        'subtotal': quantity * product.price, 
                        'pk': product.pk,
                    })
                    cart_total = sum(item['product'].price * item['quantity'] for item in cart_items)

        context = {
            'cart': cart, # Será None para anónimos
            'cart_items': cart_items, # Lista de DB objects o dicts/temp objects
            'cart_total': cart_total, # Total calculado
        }
        return render(request, self.template_name, context)
# =======================================================
# AÑADIR AL CARRITO (Añadido/Corregido)
# =======================================================
class AddToCartView(View): # LoginRequiredMixin eliminado
    """
    Añade un producto al carrito, usando DB (Logueado) o Session (Anónimo).
    """
    def post(self, request, product_pk):
        product = get_object_or_404(Product, pk=product_pk)
        
        try:
            quantity = int(request.POST.get('quantity', 1))
            if quantity < 1:
                quantity = 1
        except ValueError:
            quantity = 1
            
        cart = get_or_create_cart(request) # Devuelve Order (logueado) o None (anónimo)
        
        # --- LÓGICA DE MANEJO DEL CARRITO ---
        if cart:
            # 1. USUARIO LOGUEADO (cart es un objeto Order)
            
            # Línea 88: Ya no falla porque 'cart' es un objeto Order.
            cart_item = cart.order_products.filter(product=product).first() 

            if cart_item:
                # UPDATE (DB)
                cart_item.quantity = F('quantity') + quantity 
                cart_item.save(update_fields=['quantity'])
                cart_item.refresh_from_db() 
                messages.success(request, f"Se ha añadido {quantity} unidad(es) de '{product.name}'. Cantidad total: {cart_item.quantity}")
            else:
                # CREATE (DB)
                OrderProduct.objects.create(
                    order=cart,
                    product=product,
                    quantity=quantity
                )
                messages.success(request, f"'{product.name}' se ha añadido al carrito.")
                
        else:
            # 2. USUARIO ANÓNIMO (cart es None, usamos la sesión)
            
            cart_session = request.session.get('cart_session', {})
            product_pk_str = str(product_pk) 

            if product_pk_str in cart_session:
                # UPDATE (SESSION)
                cart_session[product_pk_str]['quantity'] += quantity
                messages.success(request, f"Se ha añadido {quantity} unidad(es) de '{product.name}'. Cantidad total en carrito: {cart_session[product_pk_str]['quantity']}")
            else:
                # CREATE (SESSION)
                cart_session[product_pk_str] = {
                    'quantity': quantity,
                    'price': str(product.price) 
                }
                messages.success(request, f"'{product.name}' se ha añadido al carrito.")
            
            # Guardar y marcar la sesión
            request.session['cart_session'] = cart_session
            request.session.modified = True 
            
        return redirect('cart_detail')
# =======================================================
# ACTUALIZAR CANTIDAD EN EL CARRITO
# =======================================================
class UpdateCartSessionView(View):
    """Actualiza la cantidad de un ítem existente en el carrito de la sesión (Anónimo)."""
    def post(self, request, product_pk):
        if request.user.is_authenticated:
            # Protección: si un usuario logueado intenta usar esta URL, redirigir a la vista DB
            return redirect('cart_detail')

        cart_session = request.session.get('cart_session', {})
        product_pk_str = str(product_pk)

        # 1. Obtener la nueva cantidad
        try:
            new_quantity = int(request.POST.get('quantity', 0))
        except ValueError:
            new_quantity = -1
        
        # Necesitamos el objeto Product para el nombre y el stock
        product = get_object_or_404(Product, pk=product_pk)

        # 2. Lógica de Actualización/Eliminación
        if product_pk_str in cart_session:  
            if new_quantity <= 0:
                # ELIMINAR
                del cart_session[product_pk_str]
                messages.info(request, f"'{product.name}' ha sido eliminado del carrito.")
            else:
                # ACTUALIZAR
                # Opcional: limitar al stock disponible
                if new_quantity >   product.stock:
                    new_quantity = product.stock
                    messages.warning(request, f"Solo quedan {product.stock} unidades de '{product.name}'. Cantidad limitada.")
                else:
                    cart_session[product_pk_str]['quantity'] = new_quantity
                    messages.success(request, f"Cantidad de '{product.name}' actualizada a {new_quantity}.")
        
            # 3. Guardar sesión
            request.session['cart_session'] = cart_session
            request.session.modified = True 
            
        return redirect('cart_detail')
    
class UpdateCartItemView(View):
    """Actualiza la cantidad de un ítem existente en el carrito."""
    def post(self, request, item_pk):
        cart_item = get_object_or_404(OrderProduct, pk=item_pk)
        cart = get_or_create_cart(request) 
        
        if cart_item.order.pk != cart.pk:
            messages.error(request, "El ítem no pertenece a tu carrito activo.")
            return redirect('cart_detail')
            
        try:
            new_quantity = int(request.POST.get('quantity', 0))
        except ValueError:
            new_quantity = -1

        if new_quantity <= 0:
            item_name = cart_item.product.name
            cart_item.delete()
            messages.info(request, f"'{item_name}' ha sido eliminado del carrito.")
        else:
            cart_item.quantity = new_quantity
            cart_item.save(update_fields=['quantity'])
            messages.success(request, f"Cantidad de '{cart_item.product.name}' actualizada a {new_quantity}.")

        return redirect('cart_detail')