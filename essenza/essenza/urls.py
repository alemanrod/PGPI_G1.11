from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from product.views import CatalogDetailView, CatalogView, DashboardView

urlpatterns = [
    path("info/", include("info.urls")),
    path("user/", include("user.urls")),
    path("admin/", admin.site.urls),
    path("product/", include("product.urls")),
    path("", DashboardView.as_view(), name="dashboard"),
    path("catalog/", CatalogView.as_view(), name="catalog"),
    path("catalog/<int:pk>/", CatalogDetailView.as_view(), name="catalog_detail"),
    path("cart/", include("cart.urls")),
    path("order/", include("order.urls")),
]

# Arreglo para muestra de imágenes en producción
urlpatterns += [
    re_path(
        r"^media/(?P<path>.*)$",
        serve,
        {
            "document_root": settings.MEDIA_ROOT,
        },
    ),
]
