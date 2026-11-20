"""
Requests and responses of the place lookups: search, geocoding, descriptions, recommendations.

These document and validate what the providers in ``adventures.providers`` return after the
services in ``adventures.services.places`` normalize it. They are not model serializers.
"""

from rest_framework import serializers

from adventures.services.places.photos import DEFAULT_SIZE, MAX_SIZE, PHOTO_NAME_RE, PHOTO_REFERENCE_RE
from adventures.services.recommendations.categories import CATEGORY_CHOICES


class LanguageQuerySerializer(serializers.Serializer):
    """The `lang` parameter shared by every lookup that returns names or text."""

    lang = serializers.CharField(
        required=False,
        help_text=(
            "Language for names and text, e.g. `de`. Defaults to the signed-in user's interface language "
            "(`X-AdventureLog-Locale`, then `Accept-Language`)."
        ),
    )


class PlaceSearchQuerySerializer(LanguageQuerySerializer):
    q = serializers.CharField(
        help_text='What to look for: a name or address, or `lat,lon` to find what is at a point.'
    )


class PlaceSearchResultSerializer(serializers.Serializer):
    name = serializers.CharField(allow_null=True)
    display_name = serializers.CharField(allow_null=True, help_text='The full address or label.')
    lat = serializers.FloatField(allow_null=True)
    lon = serializers.FloatField(allow_null=True)
    place_id = serializers.CharField(allow_null=True, help_text='Pass to `/api/places/details/`.')
    type = serializers.CharField(allow_null=True)
    types = serializers.ListField(child=serializers.CharField())
    category = serializers.CharField(allow_null=True, help_text='A location category name that fits.')
    description = serializers.CharField(allow_null=True)
    website = serializers.CharField(allow_null=True)
    phone_number = serializers.CharField(allow_null=True)
    google_maps_url = serializers.CharField(allow_null=True)
    importance = serializers.FloatField(allow_null=True)
    rating = serializers.FloatField(allow_null=True)
    review_count = serializers.IntegerField(allow_null=True)
    photos = serializers.ListField(
        child=serializers.CharField(),
        help_text='Photo addresses on this server (`/api/places/photo/?...`); the Google key is never included.',
    )
    addresstype = serializers.CharField(allow_null=True)
    provider = serializers.CharField(allow_null=True, help_text='`google` or `osm`.')
    powered_by = serializers.CharField(allow_null=True)


class PlaceSearchResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    results = PlaceSearchResultSerializer(many=True)
    provider_used = serializers.CharField(allow_null=True, help_text='The provider whose results were returned.')
    providers_attempted = serializers.ListField(child=serializers.CharField())
    warning = serializers.CharField(
        required=False, help_text='Present when every provider failed; `results` is then empty.'
    )


class PlaceDetailsQuerySerializer(LanguageQuerySerializer):
    place_id = serializers.CharField(help_text='A `place_id` from a search result.')
    name = serializers.CharField(required=False, default='', help_text='Used to search again if the id is unknown.')


class PlaceDetailsSerializer(serializers.Serializer):
    name = serializers.CharField(allow_null=True)
    description = serializers.CharField(allow_null=True)
    formatted_address = serializers.CharField(allow_null=True)
    types = serializers.ListField(child=serializers.CharField())
    rating = serializers.FloatField(allow_null=True)
    review_count = serializers.IntegerField(allow_null=True)
    website = serializers.CharField(allow_null=True)
    phone_number = serializers.CharField(allow_null=True)
    google_maps_url = serializers.CharField(allow_null=True)
    source = serializers.CharField(allow_null=True)
    provider_used = serializers.CharField(allow_null=True)


class ReverseGeocodeQuerySerializer(LanguageQuerySerializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)


class ReverseGeocodeSerializer(serializers.Serializer):
    display_name = serializers.CharField(help_text='e.g. `Boulder, Colorado, US`.')
    location_name = serializers.CharField(allow_null=True, help_text='The best name for a place at this point.')
    country = serializers.CharField(allow_null=True)
    country_id = serializers.CharField(allow_null=True, help_text='ISO alpha-2 code.')
    region = serializers.CharField(allow_null=True)
    region_id = serializers.CharField(allow_null=True)
    region_visited = serializers.BooleanField(help_text='Whether you have marked this region visited.')
    city = serializers.CharField(allow_null=True)
    city_id = serializers.CharField(allow_null=True)
    city_visited = serializers.BooleanField()
    provider = serializers.CharField(required=False)


class DescriptionQuerySerializer(serializers.Serializer):
    name = serializers.CharField(help_text='The place or topic to describe.')
    source = serializers.ChoiceField(choices=['wikipedia', 'google'], default='wikipedia')
    lang = serializers.CharField(required=False, help_text='Wikipedia language, e.g. `en`. Defaults to English.')
    place_id = serializers.CharField(required=False, help_text='With `source=google`, describe this exact place.')


class DescriptionSerializer(serializers.Serializer):
    title = serializers.CharField(allow_null=True)
    extract = serializers.CharField(help_text='Plain-text description.')
    source = serializers.CharField(required=False, help_text='`google` for Google descriptions.')
    lang = serializers.CharField(required=False, help_text='The Wikipedia language used.')


class ImageLookupQuerySerializer(serializers.Serializer):
    name = serializers.CharField(help_text='The place or topic to find pictures of.')
    lang = serializers.CharField(required=False, help_text='Wikipedia language, e.g. `en`.')


class PlacePhotoQuerySerializer(serializers.Serializer):
    name = serializers.RegexField(
        PHOTO_NAME_RE, required=False,
        help_text='A Google photo name, `places/<id>/photos/<id>`. Give this or `reference`.',
    )
    reference = serializers.RegexField(
        PHOTO_REFERENCE_RE, required=False,
        help_text='A legacy Google photo reference. Give this or `name`.',
    )
    size = serializers.IntegerField(
        required=False, default=DEFAULT_SIZE, min_value=1, max_value=MAX_SIZE,
        help_text='Longest side in pixels.',
    )

    def validate(self, attrs):
        if bool(attrs.get('name')) == bool(attrs.get('reference')):
            raise serializers.ValidationError('Give exactly one of `name` or `reference`.')
        return attrs


class WikipediaImageSerializer(serializers.Serializer):
    source = serializers.URLField()
    width = serializers.IntegerField(allow_null=True)
    height = serializers.IntegerField(allow_null=True)
    title = serializers.CharField(allow_null=True)
    type = serializers.ChoiceField(choices=['original', 'thumbnail'])


class ImageLookupSerializer(serializers.Serializer):
    images = WikipediaImageSerializer(many=True)


class RecommendationQuerySerializer(LanguageQuerySerializer):
    category = serializers.ChoiceField(
        choices=CATEGORY_CHOICES,
        help_text='What to look for. `tourism` is the older name of `attractions`.',
    )
    lat = serializers.FloatField(required=False, min_value=-90, max_value=90)
    lon = serializers.FloatField(required=False, min_value=-180, max_value=180)
    location = serializers.CharField(
        required=False, help_text='A place name to search around, instead of `lat` and `lon`.'
    )
    radius = serializers.FloatField(default=5000, min_value=1, help_text='Meters. At most 50000.')
    sources = serializers.ChoiceField(
        choices=['google', 'osm', 'both'],
        default='both',
        help_text='`both` uses Google, and tops up with OpenStreetMap when Google finds few places.',
    )
    limit = serializers.IntegerField(default=30, min_value=1, max_value=50)

    def validate_radius(self, value):
        return min(value, 50000)

    def validate(self, attrs):
        if (attrs.get('lat') is None or attrs.get('lon') is None) and not attrs.get('location'):
            raise serializers.ValidationError('Send lat and lon, or a location to search around.')
        return attrs


class RecommendationSerializer(serializers.Serializer):
    id = serializers.CharField()
    external_id = serializers.CharField()
    place_id = serializers.CharField(allow_null=True, help_text='A Google place id, when Google knows the place.')
    source = serializers.CharField(help_text='The provider the result mainly comes from: `google` or `osm`.')
    sources = serializers.ListField(child=serializers.CharField(), help_text='Every provider that reported it.')
    category = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    address = serializers.CharField(allow_null=True)
    distance_km = serializers.FloatField(allow_null=True)
    rating = serializers.FloatField(allow_null=True)
    review_count = serializers.IntegerField(allow_null=True)
    price_level = serializers.IntegerField(allow_null=True, help_text='0 (free) to 4 (very expensive).')
    types = serializers.ListField(child=serializers.CharField())
    primary_type = serializers.CharField(allow_null=True)
    business_status = serializers.CharField(allow_null=True)
    is_open_now = serializers.BooleanField(allow_null=True)
    opening_hours = serializers.ListField(child=serializers.CharField(), allow_null=True)
    phone_number = serializers.CharField(allow_null=True)
    website = serializers.CharField(allow_null=True)
    google_maps_url = serializers.CharField(allow_null=True)
    photos = serializers.ListField(child=serializers.CharField())
    is_verified = serializers.BooleanField()
    quality_score = serializers.FloatField(help_text='0 to 100; results are sorted by it.')
    osm_type = serializers.CharField(required=False, allow_null=True)
    wikipedia = serializers.CharField(required=False, allow_null=True)
    wikidata = serializers.CharField(required=False, allow_null=True)
    stars = serializers.CharField(required=False, allow_null=True)
    cuisine = serializers.CharField(required=False, allow_null=True)


class RecommendationSourcesSerializer(serializers.Serializer):
    google = serializers.IntegerField()
    osm = serializers.IntegerField()
    merged = serializers.IntegerField(help_text='Places both providers reported, combined into one result.')


class RecommendationResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    category = serializers.CharField()
    results = RecommendationSerializer(many=True)
    sources_used = RecommendationSourcesSerializer()
    warnings = serializers.ListField(child=serializers.CharField(), help_text='Problems with one provider.')
