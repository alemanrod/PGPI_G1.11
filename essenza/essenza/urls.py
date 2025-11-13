from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from info.views import info_view
from product.views import BaseView

urlpatterns = [
    path("info/", info_view, name="info-home"),
    path("user/", include("user.urls")),
    path("admin/", admin.site.urls),
    path("product/", include("product.urls")),
    path("", BaseView.as_view(), name="home"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
