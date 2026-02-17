import os
from django.conf import settings
from django.db.models import Q
from .models import Location, ContentImage, ChecklistItem, Collection, Note, Transportation, Checklist, Visit, Category, ContentAttachment, Lodging, CollectionInvite, Trail, Activity, CollectionItineraryItem, CollectionItineraryDay, CollectionTemplate, AuditLog, TransportationType, LodgingType, AdventureType, ActivityType
from rest_framework import serializers
from main.utils import CustomModelSerializer
from users.serializers import CustomUserDetailsSerializer
from worldtravel.serializers import CountrySerializer, RegionSerializer, CitySerializer
from geopy.distance import geodesic
from integrations.models import ImmichIntegration
from adventures.utils.geojson import gpx_to_geojson
from adventures.utils.visit_status import VisitStatusMixin
from adventures.utils.serializer_mixins import OwnershipSerializerMixin, MediaSerializerMixin, RatingCountMixin
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


def _convert_to_usd(amount, currency_code):
    """
    Convert an amount from any currency to USD using stored exchange rates.
    Returns the amount in USD, or the original amount if no rate is found.
    ExchangeRate.rate stores "1 USD = X currency", so USD = amount / rate.
    """
    if not amount or not currency_code:
        return float(amount) if amount else 0.0

    currency_code = str(currency_code).upper()
    if currency_code == 'USD':
        return float(amount)

    from worldtravel.models import ExchangeRate
    try:
        rate = ExchangeRate.objects.get(currency_code=currency_code)
        if rate.rate and rate.rate > 0:
            return float(amount) / float(rate.rate)
    except ExchangeRate.DoesNotExist:
        pass

    # Fallback: return original amount (treat as USD)
    return float(amount)


def _convert_from_usd(amount_usd, target_currency_code):
    """
    Convert an amount from USD to a target currency.
    ExchangeRate.rate stores "1 USD = X currency", so target = amount_usd * rate.
    """
    if not amount_usd or not target_currency_code:
        return float(amount_usd) if amount_usd else 0.0

    target_currency_code = str(target_currency_code).upper()
    if target_currency_code == 'USD':
        return float(amount_usd)

    from worldtravel.models import ExchangeRate
    try:
        rate = ExchangeRate.objects.get(currency_code=target_currency_code)
        if rate.rate and rate.rate > 0:
            return float(amount_usd) * float(rate.rate)
    except ExchangeRate.DoesNotExist:
        pass

    # Fallback: return USD amount
    return float(amount_usd)


def _get_entity_currency(entity, entity_type):
    """
    Get the display currency for an entity.
    Priority: country currency > most common visit currency > USD.
    """
    # 1. Try country currency
    candidates = []
    if entity_type == 'transportation':
        candidates = [
            getattr(entity, 'origin_country', None),
            getattr(entity, 'destination_country', None),
        ]
    else:
        candidates = [getattr(entity, 'country', None)]

    for country in candidates:
        if country:
            code = getattr(country, 'currency_code', None)
            if code and str(code).strip():
                return str(code).strip()

    # 2. Fallback: most common currency across visits
    visits_rel = getattr(entity, 'visits', None)
    if visits_rel:
        visits_with_price = visits_rel.filter(total_price__isnull=False)
        if visits_with_price.exists():
            from collections import Counter
            currencies = Counter(
                str(v.total_price_currency) for v in visits_with_price
                if v.total_price_currency and str(v.total_price_currency) != 'USD'
            )
            if currencies:
                return currencies.most_common(1)[0][0]

    return 'USD'


def _calculate_price_tier(entity, entity_type='location'):
    """
    Calculate price tier (1-4) based on local comparison within same country.

    💰      = budget-friendly (bottom 25%)
    💰💰     = moderate (25-50%)
    💰💰💰   = expensive (50-75%)
    💰💰💰💰   = premium (top 25%)

    Returns dict with tier and context, or None if insufficient data.
    """
    from django.db.models import Avg, F, FloatField
    from django.db.models.functions import Cast

    # Get the entity's average price per user
    if entity_type == 'location':
        country = entity.country
        model_class = Location
        visits_relation = 'visits'
    elif entity_type == 'transportation':
        country = entity.origin_country
        model_class = Transportation
        visits_relation = 'visits'
    elif entity_type == 'lodging':
        country = entity.country
        model_class = Lodging
        visits_relation = 'visits'
    else:
        return None

    # Get this entity's average price per user (only require total_price)
    entity_visits = entity.visits.filter(total_price__isnull=False)

    if not entity_visits.exists():
        return None

    # Calculate this entity's price per user in USD (default number_of_people to 1)
    total_price_usd = sum(_convert_to_usd(v.total_price.amount, v.total_price_currency) for v in entity_visits)
    total_people = sum(v.number_of_people or 1 for v in entity_visits)

    if total_people == 0:
        return None

    entity_price = total_price_usd / total_people

    # If no country, show fallback tier with "Global" label
    if not country:
        return {
            'tier': 2,  # Default to moderate
            'country_code': None,
            'country_name': 'Global',
            'sample_size': 1,
            'percentile': 50.0
        }

    # Get all entities of same type in same country with pricing data
    if entity_type == 'location':
        same_country = model_class.objects.filter(country=country)
    elif entity_type == 'transportation':
        same_country = model_class.objects.filter(origin_country=country)
    else:  # lodging
        same_country = model_class.objects.filter(country=country)

    # Calculate prices for all entities in same country in USD (only require total_price)
    all_prices = []
    for e in same_country.prefetch_related('visits'):
        visits = e.visits.filter(total_price__isnull=False)
        if visits.exists():
            t_price_usd = sum(_convert_to_usd(v.total_price.amount, v.total_price_currency) for v in visits)
            t_people = sum(v.number_of_people or 1 for v in visits)  # Default to 1
            if t_people > 0:
                all_prices.append(t_price_usd / t_people)

    if len(all_prices) < 2:
        # Not enough data for comparison, show fallback tier with country info
        return {
            'tier': 2,  # Default to moderate
            'country_code': country.country_code,
            'country_name': country.name,
            'sample_size': 1,
            'percentile': 50.0
        }

    # Calculate percentile rank
    all_prices.sort()
    rank = sum(1 for p in all_prices if p <= entity_price)
    percentile = (rank / len(all_prices)) * 100

    # Determine tier based on percentile
    if percentile <= 25:
        tier = 1  # 💰 budget
    elif percentile <= 50:
        tier = 2  # 💰💰 moderate
    elif percentile <= 75:
        tier = 3  # 💰💰💰 expensive
    else:
        tier = 4  # 💰💰💰💰 premium

    return {
        'tier': tier,
        'country_code': country.country_code,
        'country_name': country.name,
        'sample_size': len(all_prices),
        'percentile': round(percentile, 1)
    }


class TransportationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportationType
        fields = ['id', 'key', 'name', 'icon', 'display_order']


class LodgingTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LodgingType
        fields = ['id', 'key', 'name', 'icon', 'display_order']


class AdventureTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdventureType
        fields = ['id', 'key', 'name', 'icon', 'display_order']


class ActivityTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityType
        fields = ['id', 'key', 'name', 'icon', 'color', 'display_order']


class ContentImageSerializer(OwnershipSerializerMixin, CustomModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True, default=None)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = ContentImage
        fields = ['id', 'image', 'is_primary', 'user', 'immich_id', 'user_username', 'is_owner']
        read_only_fields = ['id', 'user', 'user_username', 'is_owner']

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
    
class AttachmentSerializer(OwnershipSerializerMixin, CustomModelSerializer):
    extension = serializers.SerializerMethodField()
    geojson = serializers.SerializerMethodField()
    user_username = serializers.CharField(source='user.username', read_only=True, default=None)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = ContentAttachment
        fields = ['id', 'file', 'extension', 'name', 'user', 'geojson', 'user_username', 'is_owner']
        read_only_fields = ['id', 'user', 'user_username', 'is_owner']

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
    
class CategorySerializer(OwnershipSerializerMixin, serializers.ModelSerializer):
    num_locations = serializers.SerializerMethodField()
    is_public = serializers.BooleanField(source='is_global', default=True)
    is_owned = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'display_name', 'icon', 'num_locations', 'is_public', 'is_owned']
        read_only_fields = ['id', 'num_locations', 'is_owned']

    def validate_name(self, value):
        return value.lower()

    def create(self, validated_data):
        validated_data['name'] = validated_data['name'].lower()
        # User is set by perform_create in the view
        return Category.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if 'name' in validated_data:
            instance.name = validated_data['name'].lower()
        instance.save()
        return instance

    def get_num_locations(self, obj):
        request = self.context.get('request')
        if getattr(settings, 'COLLABORATIVE_MODE', False):
            # In collaborative mode: count user's locations + public locations using this category
            if request and request.user.is_authenticated:
                return Location.objects.filter(
                    Q(user=request.user) | Q(is_public=True),
                    category=obj
                ).distinct().count()
            return Location.objects.filter(category=obj, is_public=True).count()
        # In normal mode, count only user's locations
        if obj.user:
            return Location.objects.filter(category=obj, user=obj.user).count()
        return 0



class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for audit log entries in collaborative mode."""
    user_username = serializers.CharField(source='user.username', read_only=True, default='Unknown')
    content_type_name = serializers.SerializerMethodField()
    is_revertible = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ['id', 'user_username', 'action', 'object_repr', 'changes', 'timestamp', 'content_type_name', 'is_revertible']
        read_only_fields = fields

    def get_content_type_name(self, obj):
        return obj.content_type.model if obj.content_type else None

    def get_is_revertible(self, obj):
        """Determine if this audit log entry can be reverted."""
        from adventures.models import Location, ContentImage, ContentAttachment

        # Can't revert if no object_id
        if not obj.object_id:
            return False

        model_class = obj.content_type.model_class()

        if obj.action == 'create':
            # Can revert create by deleting the object (if it still exists)
            try:
                if model_class == ContentImage:
                    return ContentImage.objects.filter(id=obj.object_id, is_deleted=False).exists()
                elif model_class == ContentAttachment:
                    return ContentAttachment.objects.filter(id=obj.object_id, is_deleted=False).exists()
                else:
                    return model_class.objects.filter(pk=obj.object_id).exists()
            except Exception:
                return False

        elif obj.action == 'update':
            # Can revert update if object exists and we have old values
            if not obj.changes:
                return False
            try:
                return model_class.objects.filter(pk=obj.object_id).exists()
            except Exception:
                return False

        elif obj.action == 'delete':
            # Can revert delete if object is soft-deleted (images/attachments only)
            try:
                if model_class == ContentImage:
                    return ContentImage.objects.filter(id=obj.object_id, is_deleted=True).exists()
                elif model_class == ContentAttachment:
                    return ContentAttachment.objects.filter(id=obj.object_id, is_deleted=True).exists()
                else:
                    return False  # Can't revert hard deletes
            except Exception:
                return False

        return False


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
    user_username = serializers.CharField(source='user.username', read_only=True, default=None)
    collection_info = serializers.SerializerMethodField()

    class Meta:
        model = Visit
        fields = [
            'id', 'start_date', 'end_date', 'timezone', 'notes', 'rating',
            'total_price', 'total_price_currency', 'number_of_people',
            'activities', 'location', 'transportation', 'lodging',
            'created_at', 'updated_at', 'user', 'user_username', 'collection', 'collection_info'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user', 'user_username', 'collection_info']

    def get_collection_info(self, obj):
        """Return collection name and id if visit was created from a collection."""
        if obj.collection:
            return {
                'id': str(obj.collection.id),
                'name': obj.collection.name
            }
        return None

    def create(self, validated_data):
        if not validated_data.get('end_date') and validated_data.get('start_date'):
            validated_data['end_date'] = validated_data['start_date']
        # Set the user from the request context
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
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

                                   
class LocationSerializer(OwnershipSerializerMixin, MediaSerializerMixin, RatingCountMixin, VisitStatusMixin, CustomModelSerializer):
    """
    Serializer for Location objects.

    Inherits get_is_visited from VisitStatusMixin.
    """
    images = serializers.SerializerMethodField()
    visits = VisitSerializer(many=True, read_only=False, required=False)
    attachments = AttachmentSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=False, required=False)
    is_visited = serializers.SerializerMethodField()
    is_owned = serializers.SerializerMethodField()
    contributors = serializers.SerializerMethodField()
    last_modified_by = serializers.SerializerMethodField()
    # average_rating is now a stored field, not calculated
    rating_count = serializers.SerializerMethodField()
    # Derived price metrics computed from visits
    average_price_per_user = serializers.SerializerMethodField()
    price_tier = serializers.SerializerMethodField()
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
            'id', 'name', 'description', 'rating', 'average_rating', 'rating_count', 'tags', 'location',
            'is_public', 'collections', 'created_at', 'updated_at', 'images', 'link', 'longitude',
            'latitude', 'visits', 'is_visited', 'is_owned', 'contributors', 'last_modified_by', 'category', 'attachments', 'user', 'city', 'country', 'region', 'trails',
            'price', 'price_currency', 'average_price_per_user', 'price_tier'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user', 'is_visited', 'is_owned', 'contributors', 'last_modified_by', 'average_rating', 'rating_count', 'average_price_per_user', 'price_tier']

    def get_average_price_per_user(self, obj):
        """
        Calculate average price per user from visit-level costs.
        All prices are converted to USD for computation, then converted
        to the entity's country currency for display.
        """
        visits_with_price = obj.visits.filter(total_price__isnull=False)

        if not visits_with_price.exists():
            return None

        total_price_usd = 0
        total_people = 0
        count = 0

        for visit in visits_with_price:
            total_price_usd += _convert_to_usd(visit.total_price.amount, visit.total_price_currency)
            total_people += visit.number_of_people or 1
            count += 1

        if total_people == 0:
            return None

        avg_usd = total_price_usd / total_people
        display_currency = _get_entity_currency(obj, 'location')
        display_amount = _convert_from_usd(avg_usd, display_currency)

        return {
            'amount': round(display_amount, 2),
            'currency': display_currency,
            'visit_count': count
        }

    def get_price_tier(self, obj):
        """Calculate local price tier (1-4) based on country comparison."""
        return _calculate_price_tier(obj, entity_type='location')

    def get_contributors(self, obj):
        """
        Get unique users who have contributed to this location.
        Contributors include: owner, users who added visits, images, or attachments.
        Owner is always listed first. Limited to 10 contributors.
        """
        MAX_CONTRIBUTORS = 10
        seen_ids = set()
        contributors = []

        # Add owner first (if exists)
        if obj.user:
            seen_ids.add(obj.user.id)
            contributors.append({
                'uuid': str(obj.user.uuid),
                'username': obj.user.username,
                'profile_pic': _build_profile_pic_url(obj.user),
            })

        # Collect users from visits
        for visit in obj.visits.select_related('user').all():
            if visit.user and visit.user.id not in seen_ids:
                seen_ids.add(visit.user.id)
                contributors.append({
                    'uuid': str(visit.user.uuid),
                    'username': visit.user.username,
                    'profile_pic': _build_profile_pic_url(visit.user),
                })
                if len(contributors) >= MAX_CONTRIBUTORS:
                    return contributors

        # Collect users from images (non-deleted only)
        for image in obj.images.filter(is_deleted=False).select_related('user').all():
            if image.user and image.user.id not in seen_ids:
                seen_ids.add(image.user.id)
                contributors.append({
                    'uuid': str(image.user.uuid),
                    'username': image.user.username,
                    'profile_pic': _build_profile_pic_url(image.user),
                })
                if len(contributors) >= MAX_CONTRIBUTORS:
                    return contributors

        # Collect users from attachments (non-deleted only)
        for attachment in obj.attachments.filter(is_deleted=False).select_related('user').all():
            if attachment.user and attachment.user.id not in seen_ids:
                seen_ids.add(attachment.user.id)
                contributors.append({
                    'uuid': str(attachment.user.uuid),
                    'username': attachment.user.username,
                    'profile_pic': _build_profile_pic_url(attachment.user),
                })
                if len(contributors) >= MAX_CONTRIBUTORS:
                    return contributors

        return contributors

    def get_last_modified_by(self, obj):
        """
        Get the user who last modified this location (from audit logs).
        Returns dict with username, timestamp, and profile_pic, or None.
        """
        if not getattr(settings, 'COLLABORATIVE_MODE', False):
            return None

        from django.contrib.contenttypes.models import ContentType

        ct = ContentType.objects.get_for_model(Location)
        latest_log = AuditLog.objects.filter(
            content_type=ct,
            object_id=obj.pk,
            action='update'
        ).select_related('user').order_by('-timestamp').first()

        if not latest_log or not latest_log.user:
            return None

        return {
            'uuid': str(latest_log.user.uuid),
            'username': latest_log.user.username,
            'profile_pic': _build_profile_pic_url(latest_log.user),
            'timestamp': latest_log.timestamp.isoformat(),
        }

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
                # In collaborative mode, allow public locations to be added to any collection
                is_collaborative = getattr(settings, 'COLLABORATIVE_MODE', False)
                # Check if location is public (from instance for updates, or initial data for creates)
                is_public_location = self.instance.is_public if self.instance else self.initial_data.get('is_public', False)

                if is_collaborative and is_public_location:
                    continue  # Allow public locations in collaborative mode

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
            # In collaborative mode, check user's own categories first, then public ones
            if getattr(settings, 'COLLABORATIVE_MODE', False):
                # Prefer user's own category, then fall back to public
                existing_category = Category.objects.filter(user=user, name=name).first()
                if not existing_category:
                    existing_category = Category.objects.filter(is_global=True, name=name).first()
            else:
                existing_category = Category.objects.filter(user=user, name=name).first()
            if existing_category:
                return existing_category
            category_data['name'] = name
        return category_data

    def get_or_create_category(self, category_data):
        user = self.context['request'].user
        is_collaborative = getattr(settings, 'COLLABORATIVE_MODE', False)

        if isinstance(category_data, Category):
            return category_data

        if isinstance(category_data, dict):
            name = category_data.get('name', '').lower().strip()
            display_name = category_data.get('display_name', name)
            icon = category_data.get('icon', '🌍')
        else:
            name = category_data.name.lower().strip()
            display_name = category_data.display_name
            icon = category_data.icon

        if is_collaborative:
            # In collaborative mode, check if ANY category with this name exists (public first)
            existing = Category.objects.filter(is_global=True, name=name).first()
            if existing:
                return existing
            # Then check user's own category
            existing = Category.objects.filter(user=user, name=name).first()
            if existing:
                return existing
            # Create as global public category (no duplicates)
            category = Category.objects.create(
                user=user,
                is_global=True,
                name=name,
                display_name=display_name,
                icon=icon
            )
        else:
            category, created = Category.objects.get_or_create(
                user=user,
                name=name,
                defaults={
                    'display_name': display_name,
                    'icon': icon
                }
            )
        return category

    # get_is_visited is inherited from VisitStatusMixin

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
    
class MapPinSerializer(OwnershipSerializerMixin, VisitStatusMixin, serializers.ModelSerializer):
    """Lightweight serializer for location pins on the map. Inherits get_is_visited from VisitStatusMixin."""
    is_visited = serializers.SerializerMethodField()
    is_owned = serializers.SerializerMethodField()
    category = CategorySerializer(read_only=True, required=False)
    price_tier = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = ['id', 'name', 'latitude', 'longitude', 'is_visited', 'category', 'is_owned', 'average_rating', 'price_tier']
        read_only_fields = ['id', 'name', 'latitude', 'longitude', 'is_visited', 'category', 'is_owned', 'average_rating', 'price_tier']

    # get_is_visited is inherited from VisitStatusMixin

    def get_price_tier(self, obj):
        tier_data = _calculate_price_tier(obj, 'location')
        return tier_data.get('tier') if tier_data else None


class LodgingMapPinSerializer(OwnershipSerializerMixin, VisitStatusMixin, serializers.ModelSerializer):
    """Lightweight serializer for lodging pins on the map. Inherits get_is_visited from VisitStatusMixin."""
    is_visited = serializers.SerializerMethodField()
    is_owned = serializers.SerializerMethodField()
    price_tier = serializers.SerializerMethodField()

    class Meta:
        model = Lodging
        fields = ['id', 'name', 'latitude', 'longitude', 'is_visited', 'type', 'is_owned', 'average_rating', 'price_tier']
        read_only_fields = ['id', 'name', 'latitude', 'longitude', 'is_visited', 'type', 'is_owned', 'average_rating', 'price_tier']

    # get_is_visited is inherited from VisitStatusMixin

    def get_price_tier(self, obj):
        tier_data = _calculate_price_tier(obj, 'lodging')
        return tier_data.get('tier') if tier_data else None


class TransportationMapPinSerializer(OwnershipSerializerMixin, VisitStatusMixin, serializers.ModelSerializer):
    """Lightweight serializer for transportation pins on the map. Inherits get_is_visited from VisitStatusMixin."""
    is_visited = serializers.SerializerMethodField()
    is_owned = serializers.SerializerMethodField()
    price_tier = serializers.SerializerMethodField()

    class Meta:
        model = Transportation
        fields = [
            'id', 'name', 'type', 'is_visited', 'is_owned',
            'origin_latitude', 'origin_longitude',
            'destination_latitude', 'destination_longitude',
            'from_location', 'to_location', 'average_rating', 'price_tier'
        ]
        read_only_fields = fields + ['average_rating', 'price_tier']

    # get_is_visited is inherited from VisitStatusMixin

    def get_price_tier(self, obj):
        """Return average price per user for transportation (no tier comparison)."""
        visits_with_price = obj.visits.filter(
            total_price__isnull=False,
            number_of_people__isnull=False,
            number_of_people__gt=0
        )
        if not visits_with_price.exists():
            return None

        # Calculate average price per user
        total_price = sum(float(v.total_price.amount) for v in visits_with_price)
        total_people = sum(v.number_of_people for v in visits_with_price)
        if total_people == 0:
            return None

        # Get primary currency
        currency = str(visits_with_price.first().total_price_currency)

        return {
            'average_price': round(total_price / total_people, 2),
            'currency': currency
        }


class TransportationSerializer(MediaSerializerMixin, RatingCountMixin, VisitStatusMixin, CustomModelSerializer):
    distance = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    travel_duration_minutes = serializers.SerializerMethodField()
    visits = VisitSerializer(many=True, read_only=True)
    is_visited = serializers.SerializerMethodField()
    # average_rating is now a stored field, not calculated
    rating_count = serializers.SerializerMethodField()
    # Derived price metrics computed from visits
    average_price_per_user = serializers.SerializerMethodField()
    price_tier = serializers.SerializerMethodField()
    collections = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Collection.objects.all(),
        required=False
    )
    origin_country = CountrySerializer(read_only=True)

    class Meta:
        model = Transportation
        fields = [
            'id', 'user', 'type', 'name', 'description', 'rating', 'average_rating', 'rating_count', 'price', 'price_currency',
            'link', 'flight_number', 'from_location', 'to_location', 'tags',
            'is_public', 'collections', 'created_at', 'updated_at',
            'origin_latitude', 'origin_longitude', 'destination_latitude', 'destination_longitude',
            'origin_country', 'distance', 'images', 'attachments', 'start_code', 'end_code',
            'travel_duration_minutes', 'visits', 'is_visited', 'average_price_per_user', 'price_tier'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user', 'distance', 'travel_duration_minutes', 'is_visited', 'average_rating', 'rating_count', 'average_price_per_user', 'price_tier', 'origin_country']

    def get_average_price_per_user(self, obj):
        """
        Calculate average price per user from visit-level costs, converted to USD.
        Formula: SUM(visit_total_price_in_usd) / SUM(visit_people_count)
        """
        visits_with_price = obj.visits.filter(total_price__isnull=False)

        if not visits_with_price.exists():
            return None

        total_price_usd = 0
        total_people = 0
        count = 0

        for visit in visits_with_price:
            total_price_usd += _convert_to_usd(visit.total_price.amount, visit.total_price_currency)
            total_people += visit.number_of_people or 1
            count += 1

        if total_people == 0:
            return None

        avg_usd = total_price_usd / total_people
        display_currency = _get_entity_currency(obj, 'transportation')
        display_amount = _convert_from_usd(avg_usd, display_currency)

        return {
            'amount': round(display_amount, 2),
            'currency': display_currency,
            'visit_count': count
        }

    def get_price_tier(self, obj):
        """Return average price per user for transportation (no tier comparison)."""
        avg = self.get_average_price_per_user(obj)
        if not avg:
            return None
        return {
            'average_price': avg['amount'],
            'currency': avg['currency']
        }

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
        """Calculate travel duration from the first visit's start and end dates."""
        # Get the first visit with both start and end dates
        visit = obj.visits.filter(start_date__isnull=False, end_date__isnull=False).first()
        if not visit:
            return None

        start_date = visit.start_date
        end_date = visit.end_date

        if self._is_all_day(start_date) and self._is_all_day(end_date):
            return None

        try:
            total_minutes = int((end_date - start_date).total_seconds() // 60)
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

    # get_is_visited inherited from VisitStatusMixin


class LodgingSerializer(MediaSerializerMixin, RatingCountMixin, VisitStatusMixin, CustomModelSerializer):
    images = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    visits = VisitSerializer(many=True, read_only=True)
    is_visited = serializers.SerializerMethodField()
    # average_rating is now a stored field, not calculated
    rating_count = serializers.SerializerMethodField()
    # Derived price metrics computed from visits
    average_price_per_user_per_night = serializers.SerializerMethodField()
    price_tier = serializers.SerializerMethodField()
    collections = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Collection.objects.all(),
        required=False
    )
    country = CountrySerializer(read_only=True)

    class Meta:
        model = Lodging
        fields = [
            'id', 'user', 'name', 'description', 'rating', 'average_rating', 'rating_count', 'link',
            'reservation_number', 'price', 'price_currency', 'latitude', 'longitude', 'location', 'country', 'tags', 'is_public',
            'collections', 'created_at', 'updated_at', 'type', 'images', 'attachments', 'visits', 'is_visited',
            'average_price_per_user_per_night', 'price_tier'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user', 'is_visited', 'average_rating', 'rating_count', 'average_price_per_user_per_night', 'price_tier', 'country']

    def get_average_price_per_user_per_night(self, obj):
        """
        Calculate average price per user per night from visit-level costs, converted to USD.
        Formula: SUM(visit_total_price_in_usd) / SUM(visit_people_count * visit_nights)
        """
        visits_with_price = obj.visits.filter(
            total_price__isnull=False,
            start_date__isnull=False,
            end_date__isnull=False
        )

        if not visits_with_price.exists():
            return None

        total_price_usd = 0
        total_person_nights = 0
        count = 0

        for visit in visits_with_price:
            nights = (visit.end_date.date() - visit.start_date.date()).days
            if nights < 1:
                nights = 1

            total_price_usd += _convert_to_usd(visit.total_price.amount, visit.total_price_currency)
            total_person_nights += (visit.number_of_people or 1) * nights
            count += 1

        if total_person_nights == 0:
            return None

        avg_usd = total_price_usd / total_person_nights
        display_currency = _get_entity_currency(obj, 'lodging')
        display_amount = _convert_from_usd(avg_usd, display_currency)

        return {
            'amount': round(display_amount, 2),
            'currency': display_currency,
            'visit_count': count
        }

    def get_price_tier(self, obj):
        """Calculate local price tier (1-4) based on country comparison."""
        return _calculate_price_tier(obj, entity_type='lodging')

    # get_is_visited inherited from VisitStatusMixin


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
    adventure_type = AdventureTypeSerializer(read_only=True)
    adventure_type_id = serializers.PrimaryKeyRelatedField(
        queryset=AdventureType.objects.all(),
        source='adventure_type',
        write_only=True,
        required=False,
        allow_null=True,
    )

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
            'adventure_type',
            'adventure_type_id',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user', 'shared_with', 'status', 'days_until_start', 'primary_image', 'adventure_type']

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
        return TransportationSerializer(obj.transportations.all(), many=True, context=self.context).data

    def get_notes(self, obj):
        # Only include notes if not in nested context
        if self.context.get('nested', False):
            return []
        try:
            return NoteSerializer(obj.note_set.all(), many=True, context=self.context).data
        except Exception:
            return []  # Handle missing column gracefully

    def get_checklists(self, obj):
        # Only include checklists if not in nested context
        if self.context.get('nested', False):
            return []
        try:
            return ChecklistSerializer(obj.checklist_set.all(), many=True, context=self.context).data
        except Exception:
            return []  # Handle missing column gracefully

    def get_lodging(self, obj):
        # Only include lodging if not in nested context
        if self.context.get('nested', False):
            return []
        return LodgingSerializer(obj.lodgings.all(), many=True, context=self.context).data

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

class UltraSlimCollectionSerializer(OwnershipSerializerMixin, serializers.ModelSerializer):
    location_images = serializers.SerializerMethodField()
    location_count = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    days_until_start = serializers.SerializerMethodField()
    primary_image = ContentImageSerializer(read_only=True)
    collaborators = serializers.SerializerMethodField()
    is_owned = serializers.SerializerMethodField()
    adventure_type = AdventureTypeSerializer(read_only=True)

    class Meta:
        model = Collection
        fields = [
            'id', 'user', 'name', 'description', 'is_public', 'start_date', 'end_date',
            'is_archived', 'link', 'created_at', 'updated_at', 'location_images',
            'location_count', 'shared_with', 'collaborators', 'status', 'days_until_start', 'primary_image', 'is_owned',
            'adventure_type'
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


class CollectionTemplateSerializer(CustomModelSerializer):
    class Meta:
        model = CollectionTemplate
        fields = [
            'id', 'name', 'description', 'template_data', 'is_public',
            'user', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Convert user to UUID string for consistency
        representation['user'] = str(instance.user.uuid)
        return representation
        