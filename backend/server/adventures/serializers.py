import os
from .models import Location, ContentImage, ChecklistItem, Collection, Note, Transportation, Checklist, Visit, Category, ContentAttachment, Lodging, CollectionInvite, Trail, Activity, CollectionItineraryItem, CollectionItineraryDay
from rest_framework import serializers
from main.utils import CustomModelSerializer
from users.serializers import CustomUserDetailsSerializer
from worldtravel.serializers import CountrySerializer, RegionSerializer, CitySerializer
from geopy.distance import geodesic
from integrations.models import ImmichIntegration
from adventures.utils.geojson import gpx_to_geojson
import gpxpy
import logging

logger = logging.getLogger(__name__)


def _build_profile_pic_url(user):
    """Return absolute-ish profile pic URL using PUBLIC_URL if available."""
    if not getattr(user, 'profile_pic', None):
        return None

    public_url = os.environ.get('PUBLIC_URL', 'http://127.0.0.1:8000').rstrip('/')
    public_url = public_url.replace("'", "")
    return f"{public_url}/media/{user.profile_pic.name}"


def _serialize_collaborator(user, owner_id=None, request_user=None):
    if not user:
        return None

    return {
        'uuid': str(user.uuid),
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'profile_pic': _build_profile_pic_url(user),
        'public_profile': bool(getattr(user, 'public_profile', False)),
        'is_owner': owner_id == user.id,
        'is_current_user': bool(request_user and request_user.id == user.id),
    }


class ContentImageSerializer(CustomModelSerializer):
    class Meta:
        model = ContentImage
        fields = ['id', 'image', 'is_primary', 'user', 'immich_id']
        read_only_fields = ['id', 'user']

    def to_representation(self, instance):
        # If immich_id is set, check for user integration once
        integration = None
        if instance.immich_id:
            integration = ImmichIntegration.objects.filter(user=instance.user).first()
            if not integration:
                return None  # Skip if Immich image but no integration

        # Base representation
        representation = super().to_representation(instance)

        # Prepare public URL once
        public_url = os.environ.get('PUBLIC_URL', 'http://127.0.0.1:8000').rstrip('/').replace("'", "")

        if instance.immich_id:
            # Use Immich integration URL
            representation['image'] = f"{public_url}/api/integrations/immich/{integration.id}/get/{instance.immich_id}"
        elif instance.image:
            # Use local image URL
            representation['image'] = f"{public_url}/media/{instance.image.name}"

        return representation
    
class AttachmentSerializer(CustomModelSerializer):
    extension = serializers.SerializerMethodField()
    geojson = serializers.SerializerMethodField()
    class Meta:
        model = ContentAttachment
        fields = ['id', 'file', 'extension', 'name', 'user', 'geojson']
        read_only_fields = ['id', 'user']

    def get_extension(self, obj):
        return obj.file.name.split('.')[-1]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.file:
            public_url = os.environ.get('PUBLIC_URL', 'http://127.0.0.1:8000').rstrip('/')
            #print(public_url)
            # remove any  ' from the url
            public_url = public_url.replace("'", "")
            representation['file'] = f"{public_url}/media/{instance.file.name}"
        return representation

    def get_geojson(self, obj):
        if obj.file and obj.file.name.endswith('.gpx'):
            return gpx_to_geojson(obj.file)
        return None
    
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
        return Location.objects.filter(category=obj, user=obj.user).count()
    
class TrailSerializer(CustomModelSerializer):
    provider = serializers.SerializerMethodField()
    wanderer_data = serializers.SerializerMethodField()
    wanderer_link = serializers.SerializerMethodField()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._wanderer_integration_cache = {}
    
    class Meta:
        model = Trail
        fields = ['id', 'user', 'name', 'location', 'created_at','link','wanderer_id', 'provider', 'wanderer_data', 'wanderer_link']
        read_only_fields = ['id', 'created_at', 'user', 'provider']

    def _get_wanderer_integration(self, user):
        """Cache wanderer integration to avoid multiple database queries"""
        if user.id not in self._wanderer_integration_cache:
            from integrations.models import WandererIntegration
            self._wanderer_integration_cache[user.id] = WandererIntegration.objects.filter(user=user).first()
        return self._wanderer_integration_cache[user.id]

    def get_provider(self, obj):
        if obj.wanderer_id:
            return 'Wanderer'
        # check the link to get the provider such as Strava, AllTrails, etc.
        if obj.link:
            if 'strava' in obj.link:
                return 'Strava'
            elif 'alltrails' in obj.link:
                return 'AllTrails'
            elif 'komoot' in obj.link:
                return 'Komoot'
            elif 'outdooractive' in obj.link:
                return 'Outdooractive'
        return 'External Link'
    
    def get_wanderer_data(self, obj):
        if not obj.wanderer_id:
            return None
        
        # Use cached integration
        integration = self._get_wanderer_integration(obj.user)
        if not integration:
            return None
        
        # Fetch the Wanderer trail data
        from integrations.wanderer_services import fetch_trail_by_id
        try:
            trail_data = fetch_trail_by_id(integration, obj.wanderer_id)
            if not trail_data:
                return None
            
            # Cache the trail data and link on the object to avoid refetching
            obj._wanderer_data = trail_data
            base_url = integration.server_url.rstrip('/')
            obj._wanderer_link = f"{base_url}/trails/{obj.wanderer_id}"
            
            return trail_data
        except Exception as e:
            logger.error(f"Error fetching Wanderer trail data for {obj.wanderer_id}: {e}")
            return None
    
    def get_wanderer_link(self, obj):
        if not obj.wanderer_id:
            return None
        
        # Use cached integration
        integration = self._get_wanderer_integration(obj.user)
        if not integration:
            return None
        
        base_url = integration.server_url.rstrip('/')
        return f"{base_url}/trail/view/@{integration.username}/{obj.wanderer_id}"
            
    
class ActivitySerializer(CustomModelSerializer):
    geojson = serializers.SerializerMethodField()
    
    class Meta:
        model = Activity
        fields = [
            'id', 'user', 'visit', 'trail', 'gpx_file', 'name', 'sport_type',
            'distance', 'moving_time', 'elapsed_time', 'rest_time', 'elevation_gain',
            'elevation_loss', 'elev_high', 'elev_low', 'start_date', 'start_date_local',
            'timezone', 'average_speed', 'max_speed', 'average_cadence', 'calories',
            'start_lat', 'start_lng', 'end_lat', 'end_lng', 'external_service_id', 'geojson'
        ]
        read_only_fields = ['id', 'user']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.gpx_file:
            public_url = os.environ.get('PUBLIC_URL', 'http://127.0.0.1:8000').rstrip('/').replace("'", "")
            representation['gpx_file'] = f"{public_url}/media/{instance.gpx_file.name}"
        return representation
    
    def get_geojson(self, obj):
        return gpx_to_geojson(obj.gpx_file)

class VisitSerializer(serializers.ModelSerializer):

    activities = ActivitySerializer(many=True, read_only=True, required=False)

    class Meta:
        model = Visit
        fields = ['id', 'start_date', 'end_date', 'timezone', 'notes', 'activities','location', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        if not validated_data.get('end_date') and validated_data.get('start_date'):
            validated_data['end_date'] = validated_data['start_date']
        return super().create(validated_data)


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

                                   
class LocationSerializer(CustomModelSerializer):
    images = serializers.SerializerMethodField()
    visits = VisitSerializer(many=True, read_only=False, required=False)
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
            representation['user'] = CustomUserDetailsSerializer(instance.user, context=self.context).data
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


    def get_images(self, obj):
        serializer = ContentImageSerializer(obj.images.all(), many=True, context=self.context)
        # Filter out None values from the serialized data
        return [image for image in serializer.data if image is not None]

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
                    f"The requested collection does not belong to the current user."
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

    def update(self, instance, validated_data):
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

        # Handle visits - replace all visits if provided
        if visits_data is not None:
            instance.visits.all().delete()
            for visit_data in visits_data:
                Visit.objects.create(location=instance, **visit_data)

        return instance
    
class MapPinSerializer(serializers.ModelSerializer):
    is_visited = serializers.SerializerMethodField()
    category = CategorySerializer(read_only=True, required=False)
    
    class Meta:
        model = Location
        fields = ['id', 'name', 'latitude', 'longitude', 'is_visited', 'category']
        read_only_fields = ['id', 'name', 'latitude', 'longitude', 'is_visited', 'category']
    
    def get_is_visited(self, obj):
        return obj.is_visited_status()

class TransportationSerializer(CustomModelSerializer):
    distance = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    travel_duration_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Transportation
        fields = [
            'id', 'user', 'type', 'name', 'description', 'rating', 'price', 'price_currency',
            'link', 'date', 'flight_number', 'from_location', 'to_location', 
            'is_public', 'collection', 'created_at', 'updated_at', 'end_date',
            'origin_latitude', 'origin_longitude', 'destination_latitude', 'destination_longitude',
            'start_timezone', 'end_timezone', 'distance', 'images', 'attachments', 'start_code', 'end_code',
            'travel_duration_minutes'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user', 'distance', 'travel_duration_minutes']

    def get_images(self, obj):
        serializer = ContentImageSerializer(obj.images.all(), many=True, context=self.context)
        # Filter out None values from the serialized data
        return [image for image in serializer.data if image is not None]

    def get_attachments(self, obj):
        serializer = AttachmentSerializer(obj.attachments.all(), many=True, context=self.context)
        # Filter out None values from the serialized data
        return [attachment for attachment in serializer.data if attachment is not None]

    def get_distance(self, obj):
        gpx_distance = self._get_gpx_distance_km(obj)
        if gpx_distance is not None:
            return gpx_distance

        if (
            obj.origin_latitude and obj.origin_longitude and
            obj.destination_latitude and obj.destination_longitude
        ):
            try:
                origin = (float(obj.origin_latitude), float(obj.origin_longitude))
                destination = (float(obj.destination_latitude), float(obj.destination_longitude))
                return round(geodesic(origin, destination).km, 2)
            except ValueError:
                return None
        return None

    def _get_gpx_distance_km(self, obj):
        gpx_attachments = obj.attachments.filter(file__iendswith='.gpx')
        for attachment in gpx_attachments:
            distance_km = self._parse_gpx_distance_km(attachment.file)
            if distance_km is not None:
                return distance_km
        return None

    def _parse_gpx_distance_km(self, gpx_file_field):
        try:
            with gpx_file_field.open('r') as gpx_file:
                gpx = gpxpy.parse(gpx_file)

            total_meters = 0.0

            for track in gpx.tracks:
                for segment in track.segments:
                    segment_length = segment.length_3d() or segment.length_2d()
                    if segment_length:
                        total_meters += segment_length

            for route in gpx.routes:
                route_length = route.length_3d() or route.length_2d()
                if route_length:
                    total_meters += route_length

            if total_meters > 0:
                return round(total_meters / 1000, 2)
        except Exception as exc:
            logger.warning(
                "Failed to calculate GPX distance for file %s: %s",
                getattr(gpx_file_field, 'name', 'unknown'),
                exc,
            )
        return None

    def get_travel_duration_minutes(self, obj):
        if not obj.date or not obj.end_date:
            return None

        if self._is_all_day(obj.date) and self._is_all_day(obj.end_date):
            return None

        try:
            total_minutes = int((obj.end_date - obj.date).total_seconds() // 60)
            return total_minutes if total_minutes >= 0 else None
        except Exception:
            logger.warning(
                "Failed to calculate travel duration for transportation %s",
                getattr(obj, "id", "unknown"),
                exc_info=True,
            )
            return None

    def _is_all_day(self, dt_value):
        return (
            dt_value.time().hour == 0
            and dt_value.time().minute == 0
            and dt_value.time().second == 0
            and dt_value.time().microsecond == 0
        )

class LodgingSerializer(CustomModelSerializer):
    images = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = Lodging
        fields = [
            'id', 'user', 'name', 'description', 'rating', 'link', 'check_in', 'check_out', 
            'reservation_number', 'price', 'price_currency', 'latitude', 'longitude', 'location', 'is_public',
            'collection', 'created_at', 'updated_at', 'type', 'timezone', 'images', 'attachments'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']

    def get_images(self, obj):
        serializer = ContentImageSerializer(obj.images.all(), many=True, context=self.context)
        # Filter out None values from the serialized data
        return [image for image in serializer.data if image is not None]

    def get_attachments(self, obj):
        serializer = AttachmentSerializer(obj.attachments.all(), many=True, context=self.context)
        # Filter out None values from the serialized data
        return [attachment for attachment in serializer.data if attachment is not None]

class NoteSerializer(CustomModelSerializer):

    class Meta:
        model = Note
        fields = [
            'id', 'user', 'name', 'content', 'date', 'links', 
            'is_public', 'collection', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']
    
class ChecklistItemSerializer(CustomModelSerializer):
        class Meta:
            model = ChecklistItem
            fields = [
                'id', 'user', 'name', 'is_checked', 'checklist', 'created_at', 'updated_at'
            ]
            read_only_fields = ['id', 'created_at', 'updated_at', 'user', 'checklist']
  
class ChecklistSerializer(CustomModelSerializer):
    items = ChecklistItemSerializer(many=True, source='checklistitem_set')
    
    class Meta:
        model = Checklist
        fields = [
            'id', 'user', 'name', 'date', 'is_public', 'collection', 'created_at', 'updated_at', 'items'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']
    
    def create(self, validated_data):
        items_data = validated_data.pop('checklistitem_set')
        checklist = Checklist.objects.create(**validated_data)
        
        for item_data in items_data:
            # Remove user from item_data to avoid constraint issues
            item_data.pop('user', None)
            # Set user from the parent checklist
            ChecklistItem.objects.create(
                checklist=checklist, 
                user=checklist.user,
                **item_data
            )
        return checklist
    
    def update(self, instance, validated_data):
        items_data = validated_data.pop('checklistitem_set', [])
        
        # Update Checklist fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Get current items
        current_items = instance.checklistitem_set.all()
        current_item_ids = set(current_items.values_list('id', flat=True))
        
        # Update or create items
        updated_item_ids = set()
        for item_data in items_data:
            # Remove user from item_data to avoid constraint issues
            item_data.pop('user', None)
            
            item_id = item_data.get('id')
            if item_id:
                if item_id in current_item_ids:
                    item = current_items.get(id=item_id)
                    for attr, value in item_data.items():
                        setattr(item, attr, value)
                    item.save()
                    updated_item_ids.add(item_id)
                else:
                    # If ID is provided but doesn't exist, create new item
                    ChecklistItem.objects.create(
                        checklist=instance, 
                        user=instance.user,
                        **item_data
                    )
            else:
                # If no ID is provided, create new item
                ChecklistItem.objects.create(
                    checklist=instance, 
                    user=instance.user,
                    **item_data
                )
        
        # Delete items that are not in the updated data
        items_to_delete = current_item_ids - updated_item_ids
        instance.checklistitem_set.filter(id__in=items_to_delete).delete()
        
        return instance

    def validate(self, data):
        # Check if the collection is public and the checklist is not
        collection = data.get('collection')
        is_public = data.get('is_public', False)
        if collection and collection.is_public and not is_public:
            raise serializers.ValidationError(
                'Checklists associated with a public collection must be public.'
            )
        return data

class CollectionSerializer(CustomModelSerializer):
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

    class Meta:
        model = Collection
        fields = [
            'id',
            'description',
            'user',
            'name',
            'is_public',
            'locations',
            'created_at',
            'start_date',
            'end_date',
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

    def get_collaborators(self, obj):
        request = self.context.get('request')
        request_user = getattr(request, 'user', None) if request else None

        users = []
        if obj.user:
            users.append(obj.user)
        users.extend(list(obj.shared_with.all()))

        collaborators = []
        seen = set()
        for user in users:
            if not user:
                continue
            key = str(user.uuid)
            if key in seen:
                continue
            seen.add(key)
            serialized = _serialize_collaborator(user, owner_id=obj.user_id, request_user=request_user)
            if serialized:
                collaborators.append(serialized)

        return collaborators

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

    def get_status(self, obj):
        """Calculate the status of the collection based on dates"""
        from datetime import date
        
        # If no dates, it's a folder
        if not obj.start_date or not obj.end_date:
            return 'folder'
        
        today = date.today()
        
        # Future trip
        if obj.start_date > today:
            return 'upcoming'
        
        # Past trip
        if obj.end_date < today:
            return 'completed'
        
        # Current trip
        return 'in_progress'
    
    def get_days_until_start(self, obj):
        """Calculate days until start for upcoming collections"""
        from datetime import date
        
        if not obj.start_date:
            return None
        
        today = date.today()
        
        if obj.start_date > today:
            return (obj.start_date - today).days
        
        return None

    def validate(self, attrs):
        data = super().validate(attrs)

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
                'primary_image_id': 'Cover image must come from a location in this collection.'
            })

        return data

    def _image_belongs_to_collection(self, image, collection):
        if ContentImage.objects.filter(id=image.id, location__collections=collection).exists():
            return True
        if ContentImage.objects.filter(id=image.id, visit__location__collections=collection).exists():
            return True
        return False

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
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
    
class CollectionInviteSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='collection.name', read_only=True)
    collection_owner_username = serializers.CharField(source='collection.user.username', read_only=True)
    collection_user_first_name = serializers.CharField(source='collection.user.first_name', read_only=True)
    collection_user_last_name = serializers.CharField(source='collection.user.last_name', read_only=True)
    
    class Meta:
        model = CollectionInvite
        fields = ['id', 'collection', 'created_at', 'name', 'collection_owner_username', 'collection_user_first_name', 'collection_user_last_name']
        read_only_fields = ['id', 'created_at']

class UltraSlimCollectionSerializer(serializers.ModelSerializer):
    location_images = serializers.SerializerMethodField()
    location_count = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    days_until_start = serializers.SerializerMethodField()
    primary_image = ContentImageSerializer(read_only=True)
    collaborators = serializers.SerializerMethodField()
    
    class Meta:
        model = Collection
        fields = [
            'id', 'user', 'name', 'description', 'is_public', 'start_date', 'end_date', 
            'is_archived', 'link', 'created_at', 'updated_at', 'location_images', 
            'location_count', 'shared_with', 'collaborators', 'status', 'days_until_start', 'primary_image'
        ]
        read_only_fields = fields  # All fields are read-only for listing

    def get_collaborators(self, obj):
        request = self.context.get('request')
        request_user = getattr(request, 'user', None) if request else None

        users = []
        if obj.user:
            users.append(obj.user)
        users.extend(list(obj.shared_with.all()))

        collaborators = []
        seen = set()
        for user in users:
            if not user:
                continue
            key = str(user.uuid)
            if key in seen:
                continue
            seen.add(key)
            serialized = _serialize_collaborator(user, owner_id=obj.user_id, request_user=request_user)
            if serialized:
                collaborators.append(serialized)

        return collaborators

    def get_location_images(self, obj):
        """Get primary images from locations in this collection, optimized with select_related"""
        # Filter first, then slice (removed slicing)
        images = list(
            ContentImage.objects.filter(location__collections=obj)
            .select_related('user')
        )

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
        # This uses the cached count if available, or does a simple count query
        return obj.locations.count()

    def get_status(self, obj):
        """Calculate the status of the collection based on dates"""
        from datetime import date
        
        # If no dates, it's a folder
        if not obj.start_date or not obj.end_date:
            return 'folder'
        
        today = date.today()
        
        # Future trip
        if obj.start_date > today:
            return 'upcoming'
        
        # Past trip
        if obj.end_date < today:
            return 'completed'
        
        # Current trip
        return 'in_progress'
    
    def get_days_until_start(self, obj):
        """Calculate days until start for upcoming collections"""
        from datetime import date
        
        if not obj.start_date:
            return None
        
        today = date.today()
        
        if obj.start_date > today:
            return (obj.start_date - today).days
        
        return None

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
    
class CollectionItineraryDaySerializer(CustomModelSerializer):
    class Meta:
        model = CollectionItineraryDay
        fields = ['id', 'collection', 'date', 'name', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def update(self, instance, validated_data):
        # Security: Prevent changing collection or date after creation
        # This prevents shared users from reassigning itinerary days to themselves
        validated_data.pop('collection', None)
        validated_data.pop('date', None)
        return super().update(instance, validated_data)

class CollectionItineraryItemSerializer(CustomModelSerializer):
    item = serializers.SerializerMethodField()
    start_datetime = serializers.ReadOnlyField()
    end_datetime = serializers.ReadOnlyField()
    object_name = serializers.ReadOnlyField(source='content_type.model')
    
    class Meta:
        model = CollectionItineraryItem
        fields = ['id', 'collection', 'content_type', 'object_id', 'item', 'date', 'is_global', 'order', 'start_datetime', 'end_datetime', 'created_at', 'object_name']
        read_only_fields = ['id', 'created_at', 'start_datetime', 'end_datetime', 'item', 'object_name']
    
    def update(self, instance, validated_data):
        # Security: Prevent changing collection, content_type, or object_id after creation
        # This prevents shared users from reassigning itinerary items to themselves
        # or linking items to objects they don't have permission to access
        validated_data.pop('collection', None)
        validated_data.pop('content_type', None)
        validated_data.pop('object_id', None)
        return super().update(instance, validated_data)
    
    def get_item(self, obj):
        """Return id and type for the linked item"""
        if not obj.item:
            return None
            
        return {
            'id': str(obj.item.id),
            'type': obj.content_type.model,
        }
        