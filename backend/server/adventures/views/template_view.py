from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from adventures.models import (
    CollectionTemplate, Collection, Transportation, Note, Checklist,
    ChecklistItem, Lodging, Location
)
from adventures.serializers import CollectionTemplateSerializer, CollectionSerializer


class CollectionTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing collection templates.

    Supports:
    - List own templates + public templates
    - Retrieve template details
    - Delete own templates
    - Create collection from template
    """
    serializer_class = CollectionTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return user's own templates plus all public templates"""
        user = self.request.user
        return CollectionTemplate.objects.filter(
            Q(user=user) | Q(is_public=True)
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """Only allow deletion of own templates"""
        instance = self.get_object()
        if instance.user != request.user:
            return Response(
                {"error": "You can only delete your own templates"},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='create-collection')
    def create_collection(self, request, pk=None):
        """
        Create a new collection from a template.

        The template_data contains structure for notes, checklists,
        transportations, and lodgings that will be created in the new collection.
        """
        template = self.get_object()
        user = request.user

        # Get optional name override from request
        collection_name = request.data.get('name', template.name)
        collection_description = request.data.get('description', template.description)

        # Create the new collection
        new_collection = Collection.objects.create(
            name=collection_name,
            description=collection_description,
            is_public=False,  # New collections from templates are always private
            user=user,
        )

        template_data = template.template_data or {}

        # Link locations from template (only those the user has access to)
        location_ids = template_data.get('locations', [])
        if location_ids:
            # Get locations that the user owns or are public
            accessible_locations = Location.objects.filter(
                Q(id__in=location_ids) & (Q(user=user) | Q(is_public=True))
            )
            new_collection.locations.set(accessible_locations)

        # Create notes from template
        for note_data in template_data.get('notes', []):
            Note.objects.create(
                user=user,
                collection=new_collection,
                name=note_data.get('name', 'Untitled Note'),
                content=note_data.get('content', ''),
                links=note_data.get('links', []),
                is_public=False,
            )

        # Create checklists from template
        for checklist_data in template_data.get('checklists', []):
            checklist = Checklist.objects.create(
                user=user,
                collection=new_collection,
                name=checklist_data.get('name', 'Untitled Checklist'),
                is_public=False,
            )
            # Create checklist items
            for item_data in checklist_data.get('items', []):
                ChecklistItem.objects.create(
                    user=user,
                    checklist=checklist,
                    name=item_data.get('name', ''),
                    is_checked=False,  # Always start unchecked
                )

        # Create transportations from template
        for transport_data in template_data.get('transportations', []):
            Transportation.objects.create(
                user=user,
                collection=new_collection,
                type=transport_data.get('type', 'other'),
                name=transport_data.get('name', 'Untitled Transportation'),
                description=transport_data.get('description', ''),
                from_location=transport_data.get('from_location', ''),
                to_location=transport_data.get('to_location', ''),
                is_public=False,
            )

        # Create lodgings from template
        for lodging_data in template_data.get('lodgings', []):
            Lodging.objects.create(
                user=user,
                collection=new_collection,
                type=lodging_data.get('type', 'other'),
                name=lodging_data.get('name', 'Untitled Lodging'),
                description=lodging_data.get('description', ''),
                location=lodging_data.get('location', ''),
                is_public=False,
            )

        serializer = CollectionSerializer(new_collection, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
