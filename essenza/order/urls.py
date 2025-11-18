# order/urls.py
from django.urls import include, path
from . import views

urlpatterns = [
    #path('order/', include('order.urls')),
    path('', views.CartDetailView.as_view(), name='order_home'),
    path('cart/', views.CartDetailView.as_view(), name='cart_detail'), 
    path('add/<int:product_pk>/', views.AddToCartView.as_view(), name='add_to_cart'),
    path('update/<int:item_pk>/', views.UpdateCartItemView.as_view(), name='update_cart_item'),
    path('update/session/<int:product_pk>/', views.UpdateCartSessionView.as_view(), name='update_cart_session'),

]