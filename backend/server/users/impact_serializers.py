"""Previews of what deleting an account or making a profile private would do."""

from rest_framework import serializers

from adventures.serializers.activity import TravelerSerializer


class DeletionPreviewSerializer(serializers.Serializer):
    people_released = TravelerSerializer(
        many=True, help_text='People who would get their own copy of the places of yours they travelled to.'
    )
    places_copied = serializers.IntegerField(help_text='Places of yours that someone would get a copy of.')
    locations = serializers.IntegerField(help_text='Places you own. All deleted.')
    collections = serializers.IntegerField(help_text='Collections you own. All deleted.')
    shared_collections_left = serializers.IntegerField(help_text='Trips shared with you that you would leave.')
    visits_detached = serializers.IntegerField(
        help_text='Visits at other people\'s places that others also travelled on. They stay, without you.'
    )
    visits_deleted = serializers.IntegerField(
        help_text='Visits at other people\'s places that only you travelled on. They go.'
    )
    others_uploads = serializers.IntegerField(
        help_text='Photos, attachments and activities other people added to those visits. They go too.'
    )


class PrivacyPreviewSerializer(serializers.Serializer):
    left_shared_collections = serializers.IntegerField(help_text='Trips shared with you that you would leave.')
    revoked_collection_invites = serializers.IntegerField(help_text='Invites you have not answered, which would be cancelled.')
    copies = serializers.IntegerField(help_text='Places you travelled to there that you would keep as your own copies.')
    visits_deleted = serializers.IntegerField(help_text='Visits only you travelled on. They go with the original place.')
    others_uploads = serializers.IntegerField(
        help_text='Photos, attachments and activities other people added to those visits. They go too.'
    )
