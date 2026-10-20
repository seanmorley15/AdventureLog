"""Places, their categories, and the lighter place shapes used on maps and calendars."""

from adventures.models import Location, Collection, Visit, Category
from django.db import transaction
from rest_framework import serializers
from core.serializers import CustomModelSerializer, memoized_count
from users.serializers import CustomUserDetailsSerializer, without_private_fields
from worldtravel.serializers import CountrySerializer, RegionSerializer, CitySerializer
from adventures.serializers.geo_fields import CoordinateSerializerMixin
from .activity import LocationVisitSerializer, TrailSerializer
from .common import _build_profile_pic_url
from .media import AttachmentSerializer, MediaFieldsMixin

class CategorySerializer(serializers.ModelSerializer):
    num_locations = serializers.SerializerMethodField()
    class Meta:
        model = Category
        fields = ['id', 'name', 'display_name', 'icon', 'num_locations']
        read_only_fields = ['id', 'num_locations']

    def validate_name(self, value):
        return value.lower()

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['name'] = validated_data['name'].lower()
        return Category.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if 'name' in validated_data:
            instance.name = validated_data['name'].lower()
        instance.save()
        return instance
    
    def get_num_locations(self, obj):
        # Locations nest their category, so this runs once per row. Count per category
        # for the whole owner in one query instead, and reuse it for every row.
        def counts():
            from django.db.models import Count

            return dict(
                Location.objects.filter(user_id=obj.user_id)
                .values_list('category')
                .annotate(total=Count('id'))
            )

        return memoized_count(self, 'category_counts', obj.user_id, counts).get(obj.pk, 0)


class CalendarVisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visit
        fields = ['id', 'start_date', 'end_date', 'timezone']


class CalendarLocationSerializer(serializers.ModelSerializer):
    visits = CalendarVisitSerializer(many=True, read_only=True)
    category = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = ['id', 'name', 'location', 'category', 'visits']

    def get_category(self, obj):
        if not obj.category:
            return None

        return {
            "name": obj.category.name,
            "icon": obj.category.icon,
        }


class LocationListSerializer(MediaFieldsMixin, CoordinateSerializerMixin, serializers.ModelSerializer):
    """
    Lightweight serializer for location list endpoints (e.g. /filtered/).
    Omits visits/activities/geojson, attachments, trails, and geo objects that
    dominate payload size and CPU on the locations index page.
    """
    images = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    is_visited = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    collections = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Location
        fields = [
            'id', 'name', 'rating', 'tags', 'location', 'is_public', 'collections',
            'created_at', 'updated_at', 'images', 'link', 'longitude', 'latitude',
            'is_visited', 'category', 'user', 'price', 'price_currency',
        ]
        read_only_fields = fields

    def get_category(self, obj):
        if not obj.category:
            return None
        return {
            'id': str(obj.category.id),
            'name': obj.category.name,
            'display_name': obj.category.display_name,
            'icon': obj.category.icon,
        }

    def get_is_visited(self, obj):
        annotated = getattr(obj, 'annotated_is_visited', None)
        if annotated is not None:
            return bool(annotated)
        return obj.is_visited_status()

    def get_user(self, obj):
        if not obj.user:
            return None
        return {
            'uuid': str(obj.user.uuid),
            'username': obj.user.username,
            'first_name': obj.user.first_name,
            'last_name': obj.user.last_name,
            'profile_pic': _build_profile_pic_url(obj.user),
            'public_profile': bool(getattr(obj.user, 'public_profile', False)),
        }


class LocationSerializer(MediaFieldsMixin, CoordinateSerializerMixin, CustomModelSerializer):
    images = serializers.SerializerMethodField()
    visits = LocationVisitSerializer(many=True, read_only=False, required=False)
    attachments = AttachmentSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=False, required=False)
    is_visited = serializers.SerializerMethodField()
    country = CountrySerializer(read_only=True)
    region = RegionSerializer(read_only=True)
    city = CitySerializer(read_only=True)
    collections = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=Collection.objects.all(), 
        required=False
    )
    trails = TrailSerializer(many=True, read_only=True, required=False)

    class Meta:
        model = Location
        fields = [
            'id', 'name', 'description', 'rating', 'tags', 'location', 
            'is_public', 'collections', 'created_at', 'updated_at', 'images', 'link', 'longitude', 
            'latitude', 'visits', 'is_visited', 'category', 'attachments', 'user', 'city', 'country', 'region', 'trails',
            'price', 'price_currency'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user', 'is_visited']

    # Makes it so the whole user object is returned in the serializer instead of just the user uuid
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        is_nested = self.context.get('nested', False)
        allowed_nested_fields = set(self.context.get('allowed_nested_fields', []))

        if not is_nested:
            # Full representation for standalone locations
            # The same owner repeats on every place in a list: build their payload once.
            # Only the owner sees their own account details (password settings, sharing counts).
            request = self.context.get('request')
            viewer = getattr(request, 'user', None)
            viewer_is_owner = bool(viewer and viewer.is_authenticated and viewer.id == instance.user_id)

            def owner_details():
                data = CustomUserDetailsSerializer(instance.user, context=self.context).data
                return data if viewer_is_owner else without_private_fields(data)

            representation['user'] = memoized_count(self, 'user_details', instance.user_id, owner_details)
        else:
            # Slim representation for nested contexts, but keep allowed fields
            fields_to_remove = [
                'visits', 'attachments', 'trails', 'collections',
                'user', 'city', 'country', 'region'
            ]
            for field in fields_to_remove:
                # Keep field if explicitly allowed for nested mode
                if field not in allowed_nested_fields:
                    representation.pop(field, None)

        return representation


    def validate_collections(self, collections):
        """Validate that collections are compatible with the location being created/updated"""
        
        if not collections:
            return collections
            
        user = self.context['request'].user
        
        # Get the location being updated (if this is an update operation)
        location_owner = getattr(self.instance, 'user', None) if self.instance else user
        
        # For updates, we need to check if collections are being added or removed
        current_collections = set(self.instance.collections.all()) if self.instance else set()
        new_collections_set = set(collections)
        
        collections_to_add = new_collections_set - current_collections
        collections_to_remove = current_collections - new_collections_set
        
        # Validate collections being added
        for collection in collections_to_add:
            
            # Check if user has permission to use this collection
            user_has_shared_access = collection.shared_with.filter(id=user.id).exists()
            
            if collection.user != user and not user_has_shared_access:
                raise serializers.ValidationError(
                    "The requested collection does not belong to the current user."
                )
            
            # Check location owner compatibility - both directions
            if collection.user != location_owner:
                
                # If user owns the collection but not the location, location owner must have shared access
                if collection.user == user:
                    location_owner_has_shared_access = collection.shared_with.filter(id=location_owner.id).exists() if location_owner else False
                    
                    if not location_owner_has_shared_access:
                        raise serializers.ValidationError(
                            f"Locations must be associated with collections owned by the same user or shared collections. Collection owner: {collection.user.username} Location owner: {location_owner.username if location_owner else 'None'}"
                        )
                
                # If using someone else's collection, location owner must have shared access
                else:
                    location_owner_has_shared_access = collection.shared_with.filter(id=location_owner.id).exists() if location_owner else False
                    
                    if not location_owner_has_shared_access:
                        raise serializers.ValidationError(
                            "Location cannot be added to collection unless the location owner has shared access to the collection."
                        )
        
        # Links to collections the requester cannot open are kept by the view, not removed.
        if collections_to_remove:
            from adventures.access.audience import readable_collections_q
            openable = set(
                Collection.objects.filter(pk__in=[c.pk for c in collections_to_remove])
                .filter(readable_collections_q(self.context['request']))
            )
            collections_to_remove = collections_to_remove & openable

        # Validate collections being removed - allow if user owns the collection OR owns the location
        for collection in collections_to_remove:
            user_owns_collection = collection.user == user
            user_owns_location = location_owner == user if location_owner else False
            user_has_shared_access = collection.shared_with.filter(id=user.id).exists()
            
            if not (user_owns_collection or user_owns_location or user_has_shared_access):
                raise serializers.ValidationError(
                    "You don't have permission to remove this location from one of the collections it's linked to."
                )
        
        return collections

    def validate_category(self, category_data):
        if isinstance(category_data, Category):
            return category_data
        if category_data:
            user = self.context['request'].user
            name = category_data.get('name', '').lower()
            existing_category = Category.objects.filter(user=user, name=name).first()
            if existing_category:
                return existing_category
            category_data['name'] = name
        return category_data
    
    def get_or_create_category(self, category_data):
        user = self.context['request'].user
        
        if isinstance(category_data, Category):
            return category_data
        
        if isinstance(category_data, dict):
            name = category_data.get('name', '').lower()
            display_name = category_data.get('display_name', name)
            icon = category_data.get('icon', '🌍')
        else:
            name = category_data.name.lower()
            display_name = category_data.display_name
            icon = category_data.icon

        category, created = Category.objects.get_or_create(
            user=user,
            name=name,
            defaults={
                'display_name': display_name,
                'icon': icon
            }
        )
        return category
    
    def get_is_visited(self, obj):
        return obj.is_visited_status()

    def create(self, validated_data):
        validated_data = self._pop_lat_lon(validated_data)
        category_data = validated_data.pop('category', None)
        collections_data = validated_data.pop('collections', [])
        
        location = Location.objects.create(**validated_data)

        # Handle category
        if category_data:
            category = self.get_or_create_category(category_data)
            location.category = category
        
        # Handle collections - set after location is saved
        if collections_data:
            location.collections.set(collections_data)
            
        location.save()

        return location

    @transaction.atomic
    def update(self, instance, validated_data):
        validated_data = self._pop_lat_lon(validated_data)
        category_data = validated_data.pop('category', None)
        visits_data = validated_data.pop('visits', None)
        collections_data = validated_data.pop('collections', None)

        # Update regular fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Handle category - ONLY allow the location owner to change categories
        user = self.context['request'].user
        if category_data and instance.user == user:
            # Only the owner can set categories
            category = self.get_or_create_category(category_data)
            instance.category = category
        # If not the owner, ignore category changes

        # Save the location first so that user-supplied field values (including
        # is_public) are persisted before the m2m_changed signal fires.
        instance.save()

        # Handle collections - only update if collections were provided.
        # NOTE: .set() triggers the m2m_changed signal which may override
        # is_public based on collection publicity.  By saving first we ensure
        # the user's explicit value reaches the DB before the signal runs.
        if collections_data is not None:
            instance.collections.set(collections_data)

        # Handle visits - the list sent is the full set for this place
        if visits_data is not None:
            self._sync_visits(instance, visits_data)

        return instance

    @staticmethod
    def _sync_visits(location, visits_data):
        """
        Make the place's visits match ``visits_data``. A visit sent with the id of one of
        this place's visits is updated; the rest are created; visits left out are deleted
        one by one so their photos and files go with them. An id that does not belong to
        this place is ignored, never adopted.
        """
        existing = {visit.id: visit for visit in location.visits.all()}
        kept = set()
        for visit_data in visits_data:
            visit_data = dict(visit_data)
            visit_id = visit_data.pop('id', None)
            visit_data.pop('location', None)
            visit = existing.get(visit_id)
            if visit is None:
                Visit.objects.create(location=location, **visit_data)
                continue
            for attr, value in visit_data.items():
                setattr(visit, attr, value)
            visit.save()
            kept.add(visit.id)
        for visit_id, visit in existing.items():
            if visit_id not in kept:
                visit.delete()


class MapPinSerializer(CoordinateSerializerMixin, serializers.ModelSerializer):
    is_visited = serializers.SerializerMethodField()
    category = CategorySerializer(read_only=True, required=False)
    
    class Meta:
        model = Location
        fields = ['id', 'name', 'latitude', 'longitude', 'is_visited', 'category']
        read_only_fields = ['id', 'name', 'latitude', 'longitude', 'is_visited', 'category']
    
    def get_is_visited(self, obj):
        return obj.is_visited_status()
