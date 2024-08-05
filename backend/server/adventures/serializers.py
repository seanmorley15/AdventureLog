import os
from .models import Adventure, ChecklistItem, Collection, Note, Transportation, Checklist
from rest_framework import serializers

class AdventureSerializer(serializers.ModelSerializer):

    class Meta:
        model = Adventure
        fields = '__all__' 

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.image:
            public_url = os.environ.get('PUBLIC_URL', 'http://127.0.0.1:8000').rstrip('/')
            print(public_url)
            # remove any  ' from the url
            public_url = public_url.replace("'", "")
            representation['image'] = f"{public_url}/media/{instance.image.name}"
        return representation
    
    def validate_activity_types(self, value):
        if value:
            return [activity.lower() for activity in value]
        return value
    
class TransportationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Transportation
        fields = [
            'id', 'user_id', 'type', 'name', 'description', 'rating', 
            'link', 'date', 'flight_number', 'from_location', 'to_location', 
            'is_public', 'collection', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_id']

    def validate(self, data):
        # Check if the collection is public and the transportation is not
        collection = data.get('collection')
        is_public = data.get('is_public', False)
        if collection and collection.is_public and not is_public:
            raise serializers.ValidationError(
                'Transportations associated with a public collection must be public.'
            )

        # Check if the user owns the collection
        request = self.context.get('request')
        if request and collection and collection.user_id != request.user:
            raise serializers.ValidationError(
                'Transportations must be associated with collections owned by the same user.'
            )

        return data

    def create(self, validated_data):
        # Set the user_id to the current user
        validated_data['user_id'] = self.context['request'].user
        return super().create(validated_data)

class NoteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Note
        fields = [
            'id', 'user_id', 'name', 'content', 'date', 'links', 
            'is_public', 'collection', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_id']

    def validate(self, data):
        # Check if the collection is public and the transportation is not
        collection = data.get('collection')
        is_public = data.get('is_public', False)
        if collection and collection.is_public and not is_public:
            raise serializers.ValidationError(
                'Notes associated with a public collection must be public.'
            )

        # Check if the user owns the collection
        request = self.context.get('request')
        if request and collection and collection.user_id != request.user:
            raise serializers.ValidationError(
                'Notes must be associated with collections owned by the same user.'
            )

        return data

    def create(self, validated_data):
        # Set the user_id to the current user
        validated_data['user_id'] = self.context['request'].user
        return super().create(validated_data)
    
class ChecklistItemSerializer(serializers.ModelSerializer):
        class Meta:
            model = ChecklistItem
            fields = [
                'id', 'user_id', 'name', 'is_checked', 'checklist', 'created_at', 'updated_at'
            ]
            read_only_fields = ['id', 'created_at', 'updated_at', 'user_id']
    
        def validate(self, data):
            # Check if the checklist is public and the checklist item is not
            checklist = data.get('checklist')
            is_checked = data.get('is_checked', False)
            if checklist and checklist.is_public and not is_checked:
                raise serializers.ValidationError(
                    'Checklist items associated with a public checklist must be checked.'
                )
    
            # Check if the user owns the checklist
            request = self.context.get('request')
            if request and checklist and checklist.user_id != request.user:
                raise serializers.ValidationError(
                    'Checklist items must be associated with checklists owned by the same user.'
                )
    
            return data
    
        def create(self, validated_data):
            # Set the user_id to the current user
            validated_data['user_id'] = self.context['request'].user
            return super().create(validated_data)
    
    
class Checklist(serializers.ModelSerializer):
    items = ChecklistItemSerializer(many=True, read_only=True, source='checklistitem_set')
    class Meta:
        model = Checklist
        fields = [
            'id', 'user_id', 'name', 'date', 'is_public', 'collection', 'created_at', 'updated_at', 'items'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_id']

    def validate(self, data):
        # Check if the collection is public and the checklist is not
        collection = data.get('collection')
        is_public = data.get('is_public', False)
        if collection and collection.is_public and not is_public:
            raise serializers.ValidationError(
                'Checklists associated with a public collection must be public.'
            )

        # Check if the user owns the checklist
        request = self.context.get('request')
        if request and collection and collection.user_id != request.user:
            raise serializers.ValidationError(
                'Checklists must be associated with collections owned by the same user.'
            )

        return data

    def create(self, validated_data):
        # Set the user_id to the current user
        validated_data['user_id'] = self.context['request'].user
        return super().create(validated_data)


class CollectionSerializer(serializers.ModelSerializer):
    adventures = AdventureSerializer(many=True, read_only=True, source='adventure_set')
    transportations = TransportationSerializer(many=True, read_only=True, source='transportation_set')
    notes = NoteSerializer(many=True, read_only=True, source='note_set')
    checklists = Checklist(many=True, read_only=True, source='checklist_set')

    class Meta:
        model = Collection
        # fields are all plus the adventures field
        fields = ['id', 'description', 'user_id', 'name', 'is_public', 'adventures', 'created_at', 'start_date', 'end_date', 'transportations', 'notes', 'updated_at', 'checklists']
        read_only_fields = ['id', 'created_at', 'updated_at']
