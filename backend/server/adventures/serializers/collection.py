"""Collections: the full record, the slim list shape, and invites."""

from adventures.models import ContentImage, Collection, CollectionInvite
from django.db import transaction
from rest_framework import serializers
from core.serializers import CustomModelSerializer
from adventures.utils.collection_type import assign_collection_type_from_dates, collection_lifecycle_status
from adventures.services import day_plan
from .common import _member_roles, _serialize_collaborator
from .location import LocationSerializer
from .logistics import ChecklistSerializer, LodgingSerializer, NoteSerializer, TransportationSerializer
from .media import ContentImageSerializer

class CollectionSummaryMixin:
    """Who is on a collection and where it stands in time, shared by the full and slim serializers."""

    def get_collaborators(self, obj):
        request = self.context.get('request')
        request_user = getattr(request, 'user', None) if request else None

        users = []
        if obj.user:
            users.append(obj.user)
        users.extend(list(obj.shared_with.all()))
        roles = _member_roles(obj)

        collaborators = []
        seen = set()
        for user in users:
            if not user:
                continue
            key = str(user.uuid)
            if key in seen:
                continue
            seen.add(key)
            serialized = _serialize_collaborator(
                user, owner_id=obj.user_id, request_user=request_user, role=roles.get(user.id)
            )
            if serialized:
                collaborators.append(serialized)

        return collaborators

    def get_status(self, obj):
        """Lifecycle from dates. Type is a separate field and is never returned here."""
        return collection_lifecycle_status(obj)

    def get_days_until_start(self, obj):
        """Days until a collection starts, or None once it has begun or has no start date."""
        from datetime import date

        if not obj.start_date:
            return None

        today = date.today()

        if obj.start_date > today:
            return (obj.start_date - today).days

        return None


class CollectionSerializer(CollectionSummaryMixin, CustomModelSerializer):
    collaborators = serializers.SerializerMethodField()
    locations = serializers.SerializerMethodField()
    transportations = serializers.SerializerMethodField()
    notes = serializers.SerializerMethodField()
    checklists = serializers.SerializerMethodField()
    lodging = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    days_until_start = serializers.SerializerMethodField()
    primary_image = ContentImageSerializer(read_only=True)
    primary_image_id = serializers.PrimaryKeyRelatedField(
        queryset=ContentImage.objects.all(),
        source='primary_image',
        write_only=True,
        required=False,
        allow_null=True,
    )
    # Override link as CharField so DRF's URLField doesn't reject invalid
    # values before validate_link() can clean them up.
    link = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    day_count = serializers.IntegerField(required=False, allow_null=True, min_value=1)

    class Meta:
        model = Collection
        fields = [
            'id',
            'description',
            'user',
            'name',
            'is_public',
            'visibility',
            'story_groups',
            'comment_access',
            'locations',
            'created_at',
            'start_date',
            'end_date',
            'type',
            'timezone',
            'day_count',
            'transportations',
            'notes',
            'updated_at',
            'checklists',
            'is_archived',
            'shared_with',
            'collaborators',
            'link',
            'lodging',
            'status',
            'days_until_start',
            'primary_image',
            'primary_image_id',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user', 'shared_with', 'status', 'days_until_start', 'primary_image']
        extra_kwargs = {
            'type': {'required': False},
        }

    def validate_story_groups(self, value):
        if value in (None, ''):
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError('story_groups must be an object of switches.')
        unknown = set(value) - set(Collection.STORY_GROUPS)
        if unknown:
            raise serializers.ValidationError(f'Unknown story groups: {", ".join(sorted(unknown))}')
        return {name: bool(value.get(name)) for name in Collection.STORY_GROUPS if value.get(name)}

    def _apply_visibility(self, data):
        """
        ``visibility`` is the switch; ``is_public`` from an old client maps onto it.
        Unlisted and Public need ALLOW_PUBLIC_COLLECTION_LINKS, except that a
        collection that is already public may stay public or turn private.
        """
        from django.conf import settings

        current = self.instance.visibility if self.instance else Collection.Visibility.PRIVATE
        requested = data.get('visibility')
        legacy = data.pop('is_public', None)
        if requested is None and legacy is not None:
            if legacy:
                requested = Collection.Visibility.PUBLIC
            elif current == Collection.Visibility.PUBLIC:
                requested = Collection.Visibility.PRIVATE
        if requested is None or requested == current:
            data.pop('visibility', None)
            return data
        if requested != Collection.Visibility.PRIVATE and not settings.ALLOW_PUBLIC_COLLECTION_LINKS:
            raise serializers.ValidationError({
                'visibility': 'Unlisted and public links are turned off on this server.'
            })
        data['visibility'] = requested
        return data

    def _apply_comment_access(self, data):
        """Story comments need a story: they stay off while the collection is private."""
        access = data.get('comment_access')
        if access is None or access == Collection.CommentAccess.OFF:
            return data
        visibility = data.get('visibility') or (self.instance.visibility if self.instance else None)
        if visibility in (None, Collection.Visibility.PRIVATE):
            raise serializers.ValidationError({
                'comment_access': 'Publish the story before turning comments on.'
            })
        return data

    def validate_link(self, value):
        """Convert empty or invalid URLs to None so Django doesn't reject them."""
        if not value or not value.strip():
            return None
        from django.core.validators import URLValidator
        from django.core.exceptions import ValidationError as DjangoValidationError
        validator = URLValidator()
        try:
            validator(value)
        except DjangoValidationError:
            return None
        return value

    def get_locations(self, obj):
        if self.context.get('nested', False):
            allowed_nested_fields = set(self.context.get('allowed_nested_fields', []))
            return LocationSerializer(
            obj.locations.all(), 
            many=True, 
            context={**self.context, 'nested': True, 'allowed_nested_fields': allowed_nested_fields}
        ).data
        
        return LocationSerializer(obj.locations.all(), many=True, context=self.context).data

    def get_transportations(self, obj):
        # Only include transportations if not in nested context
        if self.context.get('nested', False):
            return []
        return TransportationSerializer(obj.transportation_set.all(), many=True, context=self.context).data

    def get_notes(self, obj):
        # Only include notes if not in nested context
        if self.context.get('nested', False):
            return []
        return NoteSerializer(obj.note_set.all(), many=True, context=self.context).data

    def get_checklists(self, obj):
        # Only include checklists if not in nested context
        if self.context.get('nested', False):
            return []
        return ChecklistSerializer(obj.checklist_set.all(), many=True, context=self.context).data

    def get_lodging(self, obj):
        # Only include lodging if not in nested context
        if self.context.get('nested', False):
            return []
        return LodgingSerializer(obj.lodging_set.all(), many=True, context=self.context).data

    def _resolved_dates(self, data):
        if self.instance:
            start = data['start_date'] if 'start_date' in data else self.instance.start_date
            end = data['end_date'] if 'end_date' in data else self.instance.end_date
        else:
            start = data.get('start_date')
            end = data.get('end_date')
        return start, end

    def _instance_day_count(self):
        if self.instance is None or not self.instance.pk:
            return None
        if not hasattr(self, '_cached_instance_day_count'):
            count = day_plan.day_count(self.instance)
            self._cached_instance_day_count = count or None
        return self._cached_instance_day_count

    def _apply_collection_type(self, data):
        start, end = self._resolved_dates(data)
        count = data.get('day_count') or self._instance_day_count()
        if 'type' not in data:
            # Older clients omit type. Both dates are a trip; otherwise a folder.
            data['type'] = 'trip' if count else assign_collection_type_from_dates(start, end)
            return data
        if data['type'] == 'trip' and not count and (not start or not end):
            # A new trip still needs a plan. An existing folder may become a trip
            # with no days: linked places go to Ideas and Day 1 is not invented.
            if self.instance is None:
                raise serializers.ValidationError({
                    'type': 'A trip requires a start date and an end date, or a day count.'
                })
        return data

    def _apply_day_count(self, data):
        """Day-based trips derive end_date from the anchor and the day count."""
        requested = data.get('day_count')
        current = self._instance_day_count()
        count = requested or current
        if not count or data.get('type', getattr(self.instance, 'type', None)) != 'trip':
            data.pop('day_count', None)
            return data
        start = data['start_date'] if 'start_date' in data else getattr(self.instance, 'start_date', None)
        derived_end = day_plan.projected_date(start, count) if start else None
        if 'end_date' in data and data['end_date'] != derived_end:
            raise serializers.ValidationError({
                'end_date': 'end_date is derived from the start date and the day count. Send day_count instead.'
            })
        data['end_date'] = derived_end
        data['day_count'] = count
        return data

    def validate_timezone(self, value):
        from django.core.exceptions import ValidationError as DjangoValidationError
        from core.timezones import validate_timezone

        try:
            validate_timezone(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages[0])
        return value or 'UTC'

    @transaction.atomic
    def create(self, validated_data):
        count = validated_data.pop('day_count', None)
        collection = super().create(validated_data)
        if collection.type == 'trip':
            if count:
                day_plan.build_days(collection, count)
            else:
                day_plan.convert_collection(collection)
        return collection

    @transaction.atomic
    def update(self, instance, validated_data):
        count = validated_data.pop('day_count', None)
        current = self._instance_day_count()
        previous_type = instance.type
        resulting_type = validated_data.get('type', previous_type)

        # A trip becoming a folder keeps its day rows. Duration is not applied.
        if resulting_type == 'folder':
            return super().update(instance, validated_data)

        if current and previous_type == 'trip':
            start_changed = 'start_date' in validated_data and validated_data['start_date'] != instance.start_date
            anchor = validated_data.pop('start_date', instance.start_date)
            validated_data.pop('end_date', None)
            timezone_name = validated_data.get('timezone')
            instance = super().update(instance, validated_data)
            try:
                day_plan.set_duration(
                    instance,
                    count or current,
                    anchor=anchor if start_changed else ...,
                    timezone_name=timezone_name,
                )
            except day_plan.DayPlanError as exc:
                raise serializers.ValidationError({'day_count': exc.message, 'code': exc.code, **exc.extra})
            instance.refresh_from_db()
            return instance

        instance = super().update(instance, validated_data)
        if previous_type == 'folder' and instance.type == 'trip':
            # Saved days stay. A day count is used only when the user asked for one
            # and the collection does not already have days.
            if count and not day_plan.is_day_based(instance):
                try:
                    day_plan.build_days(instance, count)
                except day_plan.DayPlanError as exc:
                    raise serializers.ValidationError({'day_count': exc.message, 'code': exc.code, **exc.extra})
            return instance
        if instance.type == 'trip':
            if count:
                day_plan.build_days(instance, count)
            else:
                day_plan.convert_collection(instance)
        return instance

    def validate(self, attrs):
        data = super().validate(attrs)
        data = self._apply_collection_type(data)
        data = self._apply_day_count(data)
        data = self._apply_visibility(data)
        data = self._apply_comment_access(data)

        # Only validate primary image when explicitly provided
        if 'primary_image' not in data:
            return data

        primary_image = data.get('primary_image')
        if primary_image is None:
            return data

        request = self.context.get('request')
        if request and primary_image.user != request.user:
            raise serializers.ValidationError({
                'primary_image_id': 'You can only choose cover images you own.'
            })

        if self.instance and not self._image_belongs_to_collection(primary_image, self.instance):
            raise serializers.ValidationError({
                'primary_image_id': 'Cover image must come from a location or a day in this collection.'
            })

        return data

    def _image_belongs_to_collection(self, image, collection):
        from adventures.services.day_plan.files import image_belongs_to_collection

        return image_belongs_to_collection(image, collection)

    def to_representation(self, instance):
        from django.conf import settings
        from adventures.access.audience import audience_for_request

        representation = super().to_representation(instance)
        representation['day_count'] = day_plan.day_count(instance) or None
        representation['allow_public_links'] = settings.ALLOW_PUBLIC_COLLECTION_LINKS
        request = self.context.get('request')
        audience = audience_for_request(request, instance) if request is not None else None
        representation['audience'] = audience.as_dict() if audience else None
        if audience and audience.is_owner:
            representation['share_secret'] = instance.share_secret
        
        # Make it display the user uuid for the shared users instead of the PK
        shared_uuids = []
        for user in instance.shared_with.all():
            shared_uuids.append(str(user.uuid))
        representation['shared_with'] = shared_uuids
        
        # If nested, remove the heavy fields entirely from the response
        if self.context.get('nested', False):
            fields_to_remove = ['transportations', 'notes', 'checklists', 'lodging']
            for field in fields_to_remove:
                representation.pop(field, None)
        
        return representation


def _load_collection_images(collection_ids):
    """{collection id: [ContentImage]} for the places in those collections, one query."""
    from django.db.models import F

    grouped = {}
    rows = (
        ContentImage.objects.filter(location__collections__in=collection_ids)
        .select_related('user')
        .annotate(collection_pk=F('location__collections'))
    )
    for image in rows:
        grouped.setdefault(image.collection_pk, []).append(image)
    return grouped


class CollectionInviteSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='collection.name', read_only=True)
    collection_owner_username = serializers.CharField(source='collection.user.username', read_only=True)
    collection_user_first_name = serializers.CharField(source='collection.user.first_name', read_only=True)
    collection_user_last_name = serializers.CharField(source='collection.user.last_name', read_only=True)
    
    class Meta:
        model = CollectionInvite
        fields = ['id', 'collection', 'role', 'created_at', 'name', 'collection_owner_username', 'collection_user_first_name', 'collection_user_last_name']
        read_only_fields = ['id', 'created_at']


class UltraSlimCollectionSerializer(CollectionSummaryMixin, serializers.ModelSerializer):
    location_images = serializers.SerializerMethodField()
    location_count = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    days_until_start = serializers.SerializerMethodField()
    primary_image = ContentImageSerializer(read_only=True)
    collaborators = serializers.SerializerMethodField()
    day_count = serializers.SerializerMethodField()

    def get_day_count(self, obj):
        return day_plan.day_count(obj) or None
    
    class Meta:
        model = Collection
        fields = [
            'id', 'user', 'name', 'description', 'is_public', 'visibility', 'start_date', 'end_date', 'type',
            'timezone', 'day_count',
            'is_archived', 'link', 'created_at', 'updated_at', 'location_images', 
            'location_count', 'shared_with', 'collaborators', 'status', 'days_until_start', 'primary_image'
        ]
        read_only_fields = fields  # All fields are read-only for listing

    def _images_for(self, obj):
        """
        Photos of this collection's places. Serializing a page calls this once per
        collection, so the images of every collection on the page load in one query.
        """
        parent = getattr(self, 'parent', None)
        instances = getattr(parent, 'instance', None) if isinstance(parent, serializers.ListSerializer) else None
        try:
            ids = [c.pk for c in instances] if instances is not None else [obj.pk]
        except TypeError:
            ids = [obj.pk]
        if obj.pk not in ids:
            ids.append(obj.pk)
        context = self.context
        if not isinstance(context, dict) or not hasattr(self.root, '_context'):
            return _load_collection_images([obj.pk]).get(obj.pk, [])
        memo = context.setdefault('_count_memo', {})
        key = ('collection_location_images', tuple(sorted(ids, key=str)))
        if key not in memo:
            memo[key] = _load_collection_images(ids)
        return memo[key].get(obj.pk, [])

    def get_location_images(self, obj):
        """Get primary images from locations in this collection, optimized with select_related"""
        images = list(self._images_for(obj))

        def sort_key(image):
            if obj.primary_image and image.id == obj.primary_image.id:
                return (0, str(image.id))
            if image.is_primary:
                return (1, str(image.id))
            return (2, str(image.id))

        images.sort(key=sort_key)

        serializer = ContentImageSerializer(
            images,
            many=True,
            context={'request': self.context.get('request')}
        )
        # Filter out None values from the serialized data
        return [image for image in serializer.data if image is not None]

    def get_location_count(self, obj):
        """Get count of locations in this collection"""
        if hasattr(obj, 'location_count_annotated'):
            return obj.location_count_annotated
        return obj.locations.count()

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        # make it show the uuid instead of the pk for the user
        representation['user'] = str(instance.user.uuid)
        
        # Make it display the user uuid for the shared users instead of the PK
        shared_uuids = []
        for user in instance.shared_with.all():
            shared_uuids.append(str(user.uuid))
        representation['shared_with'] = shared_uuids
        return representation
