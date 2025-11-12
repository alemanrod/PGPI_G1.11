from django.views import View
from django.shortcuts import render
from django.utils import timezone
from .models import Product
from order.models import OrderProduct


class DashboardView(View):
    template_name = 'product/dashboard.html' 

    def get(self, request, *args, **kwargs):
        # Obtenemos de los datos
        order_products = OrderProduct.objects.all()
        month_ago = timezone.now() - timezone.timedelta(days=30)
        times_purchased = {}
        for order_product in order_products:
            order = order_product.order

            # ===============================================
            # IMPRESCINDIBLE QUITAR VERIFICACIÓN DE TRUE PARA QUE FUNCIONE CORRECTAMENTE
            # ===============================================

            if order.placed_at>=month_ago or True:
                if order_product.product.id in times_purchased:
                    times_purchased[order_product.product.id] += order_product.quantity
                else:
                    times_purchased[order_product.product.id] = order_product.quantity
        times_purchased_ordered = dict(sorted(times_purchased.items(), key=lambda quantity: quantity[1], reverse=True))
        most_purchased_products = list(times_purchased_ordered.keys())[:10]
        products = Product.objects.filter(is_active=True, id__in=most_purchased_products)
        print(products)
        
        return render(request, self.template_name, {'products': products})