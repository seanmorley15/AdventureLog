"""
Content access query utilities for images and attachments.

This module provides reusable functions to build access control queries
for ContentImage and ContentAttachment viewsets.
"""

from django.db.models import Q
from django.conf import settings
from django.contrib.contenttypes.models import ContentType


def build_content_access_query(user):
    """
    Build a Q object for filtering content (images/attachments) that a user can access.

    This consolidates the complex access control logic for:
    - Direct ownership
    - Access through owned locations/transportations/notes/lodging
    - Access through shared collections
    - Access through collection ownership
    - Access through visits (via location relationships)
    - Collaborative mode public content

    Args:
        user: The authenticated user

    Returns:
        Q: A Django Q object for filtering ContentImage or ContentAttachment
    """
    # Import models here to avoid circular imports
    from adventures.models import Location, Transportation, Note, Lodging, Visit

    # Get content types once for efficiency
    location_ct = ContentType.objects.get_for_model(Location)
    transportation_ct = ContentType.objects.get_for_model(Transportation)
    note_ct = ContentType.objects.get_for_model(Note)
    lodging_ct = ContentType.objects.get_for_model(Lodging)
    visit_ct = ContentType.objects.get_for_model(Visit)

    # Build the base query
    query = (
        # User owns the content directly
        Q(user=user) |

        # === LOCATIONS ===
        # Locations owned by user
        (
            Q(content_type=location_ct) &
            Q(object_id__in=Location.objects.filter(user=user).values_list('id', flat=True))
        ) |
        # Shared locations (via collections)
        (
            Q(content_type=location_ct) &
            Q(object_id__in=Location.objects.filter(collections__shared_with=user).values_list('id', flat=True))
        ) |
        # Collections owned by user containing locations
        (
            Q(content_type=location_ct) &
            Q(object_id__in=Location.objects.filter(collections__user=user).values_list('id', flat=True))
        ) |

        # === TRANSPORTATION ===
        # Transportation owned by user
        (
            Q(content_type=transportation_ct) &
            Q(object_id__in=Transportation.objects.filter(user=user).values_list('id', flat=True))
        ) |
        # Transportation shared via collections
        (
            Q(content_type=transportation_ct) &
            Q(object_id__in=Transportation.objects.filter(collections__shared_with=user).values_list('id', flat=True))
        ) |

        # === NOTES ===
        # Notes owned by user
        (
            Q(content_type=note_ct) &
            Q(object_id__in=Note.objects.filter(user=user).values_list('id', flat=True))
        ) |
        # Notes shared via collections
        (
            Q(content_type=note_ct) &
            Q(object_id__in=Note.objects.filter(collection__shared_with=user).values_list('id', flat=True))
        ) |

        # === LODGING ===
        # Lodging owned by user
        (
            Q(content_type=lodging_ct) &
            Q(object_id__in=Lodging.objects.filter(user=user).values_list('id', flat=True))
        ) |
        # Lodging shared via collections
        (
            Q(content_type=lodging_ct) &
            Q(object_id__in=Lodging.objects.filter(collections__shared_with=user).values_list('id', flat=True))
        ) |

        # === VISITS ===
        # Visits - access through location's user
        (
            Q(content_type=visit_ct) &
            Q(object_id__in=Visit.objects.filter(location__user=user).values_list('id', flat=True))
        ) |
        # Visits - access through shared locations
        (
            Q(content_type=visit_ct) &
            Q(object_id__in=Visit.objects.filter(location__collections__shared_with=user).values_list('id', flat=True))
        ) |
        # Visits - access through collections owned by user
        (
            Q(content_type=visit_ct) &
            Q(object_id__in=Visit.objects.filter(location__collections__user=user).values_list('id', flat=True))
        )
    )

    # In collaborative mode, also include content from public locations
    if getattr(settings, 'COLLABORATIVE_MODE', False):
        query |= (
            # Public locations
            (
                Q(content_type=location_ct) &
                Q(object_id__in=Location.objects.filter(is_public=True).values_list('id', flat=True))
            ) |
            # Visits from public locations
            (
                Q(content_type=visit_ct) &
                Q(object_id__in=Visit.objects.filter(location__is_public=True).values_list('id', flat=True))
            )
        )

    return query


class ContentAccessMixin:
    """
    Mixin for viewsets that need content access control (images, attachments).

    Usage:
        class MyContentViewSet(ContentAccessMixin, viewsets.ModelViewSet):
            # model_class should be set to ContentImage or ContentAttachment
            model_class = ContentImage

            def get_queryset(self):
                return self.get_accessible_content()
    """

    # Override in subclass
    model_class = None

    def get_accessible_content(self):
        """
        Get all content objects the user can access.

        Returns:
            QuerySet: Filtered queryset of content objects
        """
        if not self.request.user.is_authenticated:
            return self.model_class.objects.none()

        query = build_content_access_query(self.request.user)

        # Exclude soft-deleted content
        return self.model_class.objects.filter(query, is_deleted=False).distinct()
