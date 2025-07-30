from django.utils import timezone
import os
from .models import Location, ContentImage, ChecklistItem, Collection, Note, Transportation, Checklist, Visit, Category, ContentAttachment, Lodging
from rest_framework import serializers
from main.utils import CustomModelSerializer
from users.serializers import CustomUserDetailsSerializer
from worldtravel.serializers import CountrySerializer, RegionSerializer, CitySerializer
from geopy.distance import geodesic
from integrations.models import ImmichIntegration


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
    class Meta:
        model = ContentAttachment
        fields = ['id', 'file', 'extension', 'name', 'user']
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
    
class VisitSerializer(serializers.ModelSerializer):

    class Meta:
        model = Visit
        fields = ['id', 'start_date', 'end_date', 'timezone', 'notes']
        read_only_fields = ['id']
                                   
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

    class Meta:
        model = Location
        fields = [
            'id', 'name', 'description', 'rating', 'tags', 'location', 
            'is_public', 'collections', 'created_at', 'updated_at', 'images', 'link', 'longitude', 
            'latitude', 'visits', 'is_visited', 'category', 'attachments', 'user', 'city', 'country', 'region'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user', 'is_visited']

    # Makes it so the whole user object is returned in the serializer instead of just the user uuid
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['user'] = CustomUserDetailsSerializer(instance.user, context=self.context).data
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
        visits_data = validated_data.pop('visits', [])
        category_data = validated_data.pop('category', None)
        collections_data = validated_data.pop('collections', [])
        
        print(category_data)
        location = Location.objects.create(**validated_data)
        
        # Handle visits
        for visit_data in visits_data:
            Visit.objects.create(location=location, **visit_data)

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
        visits_data = validated_data.pop('visits', [])
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

        # Handle visits
        if has_visits:
            current_visits = instance.visits.all()
            current_visit_ids = set(current_visits.values_list('id', flat=True))

            updated_visit_ids = set()
            for visit_data in visits_data:
                visit_id = visit_data.get('id')
                if visit_id and visit_id in current_visit_ids:
                    visit = current_visits.get(id=visit_id)
                    for attr, value in visit_data.items():
                        setattr(visit, attr, value)
                    visit.save()
                    updated_visit_ids.add(visit_id)
                else:
                    new_visit = Visit.objects.create(location=instance, **visit_data)
                    updated_visit_ids.add(new_visit.id)

            visits_to_delete = current_visit_ids - updated_visit_ids
            instance.visits.filter(id__in=visits_to_delete).delete()

        # call save on the location to update the updated_at field and trigger any geocoding
        instance.save()

        return instance

class TransportationSerializer(CustomModelSerializer):
    distance = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()

    class Meta:
        model = Transportation
        fields = [
            'id', 'user', 'type', 'name', 'description', 'rating', 
            'link', 'date', 'flight_number', 'from_location', 'to_location', 
            'is_public', 'collection', 'created_at', 'updated_at', 'end_date',
            'origin_latitude', 'origin_longitude', 'destination_latitude', 'destination_longitude',
            'start_timezone', 'end_timezone', 'distance', 'images'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user', 'distance']

    def get_images(self, obj):
        serializer = ContentImageSerializer(obj.images.all(), many=True, context=self.context)
        # Filter out None values from the serialized data
        return [image for image in serializer.data if image is not None]

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

    class Meta:
        model = Lodging
        fields = [
            'id', 'user', 'name', 'description', 'rating', 'link', 'check_in', 'check_out', 
            'reservation_number', 'price', 'latitude', 'longitude', 'location', 'is_public',
            'collection', 'created_at', 'updated_at', 'type', 'timezone', 'images'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']

    def get_images(self, obj):
        serializer = ContentImageSerializer(obj.images.all(), many=True, context=self.context)
        # Filter out None values from the serialized data
        return [image for image in serializer.data if image is not None]

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
    locations = LocationSerializer(many=True, read_only=True)
    transportations = TransportationSerializer(many=True, read_only=True, source='transportation_set')
    notes = NoteSerializer(many=True, read_only=True, source='note_set')
    checklists = ChecklistSerializer(many=True, read_only=True, source='checklist_set')
    lodging = LodgingSerializer(many=True, read_only=True, source='lodging_set')

    class Meta:
        model = Collection
        fields = ['id', 'description', 'user', 'name', 'is_public', 'locations', 'created_at', 'start_date', 'end_date', 'transportations', 'notes', 'updated_at', 'checklists', 'is_archived', 'shared_with', 'link', 'lodging']
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Make it display the user uuid for the shared users instead of the PK
        shared_uuids = []
        for user in instance.shared_with.all():
            shared_uuids.append(str(user.uuid))
        representation['shared_with'] = shared_uuids
        return representation