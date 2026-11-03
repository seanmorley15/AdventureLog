from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets

from adventures.models import Category, Location
from adventures.serializers import CategorySerializer
from core.exceptions import APIError


@extend_schema_view(
    destroy=extend_schema(
        description='Its locations move to the `general` category, which is created if needed. The `general` '
        'category itself cannot be deleted (`400 protected_category`).'
    ),
)
class CategoryViewSet(viewsets.ModelViewSet):
    """Your location categories, each with a `name` (a slug), a `display_name` and an emoji `icon`."""

    openapi_tags = ['Categories & tags']
    openapi_resource_plural = 'categories'
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Category.objects.none()
        return Category.objects.filter(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.name == 'general':
            raise APIError('The general category cannot be deleted.', code='protected_category')

        # set any locations with this category to a default category called general before deleting the category, if general does not exist create it for the user
        general_category = Category.objects.filter(user=request.user, name='general').first()

        if not general_category:
            general_category = Category.objects.create(user=request.user, name='general', icon='🌍', display_name='General')
        
        Location.objects.filter(category=instance).update(category=general_category)

        return super().destroy(request, *args, **kwargs)