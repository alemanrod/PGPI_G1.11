from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from info.views import info_view
from product.views import CatalogDetailView, CatalogView, DashboardView

urlpatterns = [
    path("info/", info_view, name="info-home"),
    path("user/", include("user.urls")),
    path("admin/", admin.site.urls),
    path("product/", include("product.urls")),
    path("", DashboardView.as_view(), name="dashboard"),
    path("catalog/", CatalogView.as_view(), name="catalog"),
    path("catalog/<int:pk>/", CatalogDetailView.as_view(), name="catalog_detail"),
    path("cart/", include("cart.urls")),
    path("order/", include("order.urls")),
    path("info/", include("info.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
