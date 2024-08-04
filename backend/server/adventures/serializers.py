import os
from .models import Adventure, Collection, Note, Transportation
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
        read_only_fields = ['id', 'created_at', 'updated_at']

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
        read_only_fields = ['id', 'created_at', 'updated_at']

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
    
class CollectionSerializer(serializers.ModelSerializer):
    adventures = AdventureSerializer(many=True, read_only=True, source='adventure_set')
    transportations = TransportationSerializer(many=True, read_only=True, source='transportation_set')
    notes = NoteSerializer(many=True, read_only=True, source='note_set')

    class Meta:
        model = Collection
        # fields are all plus the adventures field
        fields = ['id', 'description', 'user_id', 'name', 'is_public', 'adventures', 'created_at', 'start_date', 'end_date', 'transportations', 'notes']
