import os
from .models import Adventure, Collection
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
    
class CollectionSerializer(serializers.ModelSerializer):
    adventures = AdventureSerializer(many=True, read_only=True, source='adventure_set')

    class Meta:
        model = Collection
        # fields are all plus the adventures field
        fields = ['id', 'description', 'user_id', 'name', 'is_public', 'adventures']


   