from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

import product.views as views

urlpatterns = [
    path("stock/", views.StockView.as_view(), name="stock"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
