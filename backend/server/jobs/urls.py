"""Routes of the jobs app. Mounted at ``api/`` by ``main.api_urls``."""

from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import BackgroundJobViewSet

router = SimpleRouter()
router.register(r'jobs', BackgroundJobViewSet, basename='jobs')

urlpatterns = [path('', include(router.urls))]
