from django.contrib import admin
from django.urls import include, path

from .views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("saude/", health, name="health"),
    path("identidade/", include("identity.urls")),
    path("", include("communities.urls")),
]
