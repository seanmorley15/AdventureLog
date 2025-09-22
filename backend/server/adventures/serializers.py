import os
from .models import Location, ContentImage, ChecklistItem, Collection, Note, Transportation, Checklist, Visit, Category, ContentAttachment, Lodging, CollectionInvite, Trail, Activity
from rest_framework import serializers
from main.utils import CustomModelSerializer
from users.serializers import CustomUserDetailsSerializer
from worldtravel.serializers import CountrySerializer, RegionSerializer, CitySerializer
from geopy.distance import geodesic
from integrations.models import ImmichIntegration
from adventures.utils.geojson import gpx_to_geojson
import logging

logger = logging.getLogger(__name__)


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
            'latitude', 'visits', 'is_visited', 'category', 'attachments', 'user', 'city', 'country', 'region', 'trails'
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
        has_visits = 'visits' in validated_data
        category_data = validated_data.pop('category', None)

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

        # Handle collections - only update if collections were provided
        if collections_data is not None:
            instance.collections.set(collections_data)

        # call save on the location to update the updated_at field and trigger any geocoding
        instance.save()

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

    class Meta:
        model = Transportation
        fields = [
            'id', 'user', 'type', 'name', 'description', 'rating', 
            'link', 'date', 'flight_number', 'from_location', 'to_location', 
            'is_public', 'collection', 'created_at', 'updated_at', 'end_date',
            'origin_latitude', 'origin_longitude', 'destination_latitude', 'destination_longitude',
            'start_timezone', 'end_timezone', 'distance', 'images', 'attachments'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user', 'distance']

    def get_images(self, obj):
        serializer = ContentImageSerializer(obj.images.all(), many=True, context=self.context)
        # Filter out None values from the serialized data
        return [image for image in serializer.data if image is not None]

    def get_attachments(self, obj):
        serializer = AttachmentSerializer(obj.attachments.all(), many=True, context=self.context)
        # Filter out None values from the serialized data
        return [attachment for attachment in serializer.data if attachment is not None]

    def get_distance(self, obj):
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

class LodgingSerializer(CustomModelSerializer):
    images = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = Lodging
        fields = [
            'id', 'user', 'name', 'description', 'rating', 'link', 'check_in', 'check_out', 
            'reservation_number', 'price', 'latitude', 'longitude', 'location', 'is_public',
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
    locations = serializers.SerializerMethodField()
    transportations = serializers.SerializerMethodField()
    notes = serializers.SerializerMethodField()
    checklists = serializers.SerializerMethodField()
    lodging = serializers.SerializerMethodField()

    class Meta:
        model = Collection
        fields = ['id', 'description', 'user', 'name', 'is_public', 'locations', 'created_at', 'start_date', 'end_date', 'transportations', 'notes', 'updated_at', 'checklists', 'is_archived', 'shared_with', 'link', 'lodging']
        read_only_fields = ['id', 'created_at', 'updated_at', 'user', 'shared_with']

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
    
    class Meta:
        model = Collection
        fields = [
            'id', 'user', 'name', 'description', 'is_public', 'start_date', 'end_date', 
            'is_archived', 'link', 'created_at', 'updated_at', 'location_images', 
            'location_count', 'shared_with'
        ]
        read_only_fields = fields  # All fields are read-only for listing

    def get_location_images(self, obj):
        """Get primary images from locations in this collection, optimized with select_related"""
        # Filter first, then slice (removed slicing)
        images = ContentImage.objects.filter(
            location__collections=obj
        ).select_related('user').prefetch_related('location')

        return ContentImageSerializer(
            images,
            many=True,
            context={'request': self.context.get('request')}
        ).data

    def get_location_count(self, obj):
        """Get count of locations in this collection"""
        # This uses the cached count if available, or does a simple count query
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
    