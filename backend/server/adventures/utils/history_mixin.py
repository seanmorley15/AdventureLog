"""
Mixin providing history and revert actions for collaborative mode.

Used by: LocationViewSet, TransportationViewSet, LodgingViewSet
"""

from django.db.models import Q
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from rest_framework.decorators import action
from rest_framework.response import Response
from adventures.models import AuditLog, ContentImage, ContentAttachment
from adventures.serializers import AuditLogSerializer


class HistoryRevertMixin:
    """
    Mixin providing history() and revert() actions for collaborative mode.

    Uses self.get_object() and derives the model class dynamically,
    so it works generically across Location, Transportation, and Lodging viewsets.
    """

    @action(detail=True, methods=['get'], url_path='history')
    def history(self, request, pk=None):
        """Get audit history for an entity and its related content (collaborative mode only)."""
        if not getattr(settings, 'COLLABORATIVE_MODE', False):
            return Response({"error": "History is only available in collaborative mode"}, status=400)

        instance = self.get_object()
        model_class = type(instance)

        # Get content types
        entity_ct = ContentType.objects.get_for_model(model_class)
        image_ct = ContentType.objects.get_for_model(ContentImage)
        attachment_ct = ContentType.objects.get_for_model(ContentAttachment)

        # Get IDs of images and attachments belonging to this entity (including soft-deleted)
        image_ids = list(instance.images.all().values_list('id', flat=True))
        attachment_ids = list(instance.attachments.all().values_list('id', flat=True))

        # Build query for all related logs
        logs_query = Q(content_type=entity_ct, object_id=instance.pk)

        if image_ids:
            logs_query |= Q(content_type=image_ct, object_id__in=image_ids)

        if attachment_ids:
            logs_query |= Q(content_type=attachment_ct, object_id__in=attachment_ids)

        logs = AuditLog.objects.filter(logs_query).select_related('user').order_by('-timestamp')[:50]
        serializer = AuditLogSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='revert/(?P<log_id>[^/.]+)')
    def revert(self, request, pk=None, log_id=None):
        """Revert a specific audit log entry (collaborative mode only)."""
        if not getattr(settings, 'COLLABORATIVE_MODE', False):
            return Response({"error": "Revert is only available in collaborative mode"}, status=400)

        instance = self.get_object()
        model_class = type(instance)
        model_name = model_class.__name__.lower()

        # Get the audit log entry
        try:
            log_entry = AuditLog.objects.get(id=log_id)
        except AuditLog.DoesNotExist:
            return Response({"error": "Audit log entry not found"}, status=404)

        # Verify the log entry belongs to this entity or its related content
        entity_ct = ContentType.objects.get_for_model(model_class)
        image_ct = ContentType.objects.get_for_model(ContentImage)
        attachment_ct = ContentType.objects.get_for_model(ContentAttachment)

        is_entity_log = log_entry.content_type == entity_ct and str(log_entry.object_id) == str(instance.pk)
        is_image_log = log_entry.content_type == image_ct and instance.images.filter(id=log_entry.object_id).exists()
        is_attachment_log = log_entry.content_type == attachment_ct and instance.attachments.filter(id=log_entry.object_id).exists()

        if not (is_entity_log or is_image_log or is_attachment_log):
            return Response({"error": f"This audit log entry does not belong to this {model_name}"}, status=403)

        # Check permission: only the user who made the change, the entity owner, or an admin can revert
        can_revert = (
            log_entry.user == request.user or
            instance.user == request.user or
            request.user.is_staff
        )
        if not can_revert:
            return Response({"error": "You don't have permission to revert this change"}, status=403)

        log_model_class = log_entry.content_type.model_class()

        try:
            if log_entry.action == 'create':
                # Revert create = delete the object
                obj = log_model_class.objects.get(pk=log_entry.object_id)
                if log_model_class in [ContentImage, ContentAttachment]:
                    obj.deleted_by = request.user
                    obj.save(update_fields=['deleted_by'])
                obj.delete()
                return Response({"success": f"Reverted creation of {log_entry.object_repr}"})

            elif log_entry.action == 'update':
                # Revert update = restore old values
                obj = log_model_class.objects.get(pk=log_entry.object_id)
                changes = log_entry.changes or {}

                for field_name, values in changes.items():
                    old_value = values.get('old')
                    if old_value is not None and hasattr(obj, field_name):
                        field = obj._meta.get_field(field_name)
                        # Handle different field types
                        if field.get_internal_type() in ['FloatField', 'DecimalField']:
                            try:
                                setattr(obj, field_name, float(old_value) if old_value != 'None' else None)
                            except (ValueError, TypeError):
                                setattr(obj, field_name, None)
                        elif field.get_internal_type() == 'IntegerField':
                            try:
                                setattr(obj, field_name, int(old_value) if old_value != 'None' else None)
                            except (ValueError, TypeError):
                                setattr(obj, field_name, None)
                        elif field.get_internal_type() == 'BooleanField':
                            setattr(obj, field_name, old_value.lower() == 'true')
                        elif field.get_internal_type() in ['CharField', 'TextField']:
                            setattr(obj, field_name, old_value if old_value != 'None' else None)
                        # Skip ForeignKey and other complex fields for now

                obj.save()
                return Response({"success": f"Reverted update of {log_entry.object_repr}"})

            elif log_entry.action == 'delete':
                # Revert delete = restore soft-deleted object
                if log_model_class == ContentImage:
                    obj = ContentImage.objects.get(pk=log_entry.object_id)
                    obj.restore()
                    return Response({"success": "Restored deleted image"})
                elif log_model_class == ContentAttachment:
                    obj = ContentAttachment.objects.get(pk=log_entry.object_id)
                    obj.restore()
                    return Response({"success": "Restored deleted attachment"})
                else:
                    return Response({"error": "Cannot revert hard delete"}, status=400)

            else:
                return Response({"error": f"Unknown action: {log_entry.action}"}, status=400)

        except log_model_class.DoesNotExist:
            return Response({"error": "Object no longer exists"}, status=404)
        except Exception as e:
            return Response({"error": f"Failed to revert: {str(e)}"}, status=500)
