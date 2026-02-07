from django.db.models import Q
from django.conf import settings
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from adventures.models import Category, Location
from adventures.serializers import CategorySerializer


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(settings, 'COLLABORATIVE_MODE', False):
            # In collaborative mode: user's own categories + public categories from others
            return Category.objects.filter(
                Q(user=self.request.user) | Q(is_global=True)
            ).distinct()
        return Category.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """Create a category, preventing duplicates in collaborative mode."""
        name = request.data.get('name', '').lower().strip()

        if getattr(settings, 'COLLABORATIVE_MODE', False):
            # Check if a public category with this name already exists
            existing = Category.objects.filter(is_global=True, name=name).first()
            if existing:
                # Return the existing category instead of creating a duplicate
                serializer = self.get_serializer(existing)
                return Response(serializer.data, status=200)

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        # User always owns their categories, is_public can be set via request data
        serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        """
        Retrieve a list of distinct categories for locations associated with the current user.
        """
        categories = self.get_queryset().distinct()
        serializer = self.get_serializer(categories, many=True)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        # Only the owner can update their category
        if instance.user != request.user:
            return Response({"error": "User does not own this category"}, status=400)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.name == 'general':
            return Response({"error": "Cannot delete the general category"}, status=400)

        # Only the owner can delete their category
        if instance.user != request.user:
            return Response({"error": "User does not own this category"}, status=400)

        # Reassign locations to global general category (or create it)
        general_category = Category.objects.filter(is_global=True, name='general').first()
        if not general_category:
            general_category = Category.objects.create(
                user=None, is_global=True, name='general', icon='🌍', display_name='General'
            )

        # Only reassign the user's own locations that use this category
        Location.objects.filter(category=instance, user=request.user).update(category=general_category)

        return super().destroy(request, *args, **kwargs)