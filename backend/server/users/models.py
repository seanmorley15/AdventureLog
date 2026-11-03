import hashlib
import secrets
import uuid
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django_resized import ResizedImageField


CURRENCY_CHOICES = (
    ('USD', 'US Dollar'),
    ('EUR', 'Euro'),
    ('GBP', 'British Pound'),
    ('JPY', 'Japanese Yen'),
    ('AUD', 'Australian Dollar'),
    ('CAD', 'Canadian Dollar'),
    ('CHF', 'Swiss Franc'),
    ('CNY', 'Chinese Yuan'),
    ('HKD', 'Hong Kong Dollar'),
    ('SGD', 'Singapore Dollar'),
    ('SEK', 'Swedish Krona'),
    ('NOK', 'Norwegian Krone'),
    ('DKK', 'Danish Krone'),
    ('NZD', 'New Zealand Dollar'),
    ('INR', 'Indian Rupee'),
    ('MXN', 'Mexican Peso'),
    ('BRL', 'Brazilian Real'),
    ('ZAR', 'South African Rand'),
    ('AED', 'UAE Dirham'),
    ('TRY', 'Turkish Lira'),
)

DATE_FORMAT_CHOICES = (
    ('locale', 'Browser default'),
    ('mdy', 'MM/DD/YYYY'),
    ('dmy', 'DD/MM/YYYY'),
    ('ymd', 'YYYY-MM-DD'),
)

BASEMAP_CHOICES = (
    ('default', 'Default'),
    ('terrain-3d', '3D Terrain'),
    ('satellite-terrain-3d', '3D Satellite Terrain'),
    ('topo-terrain-3d', '3D Topographic'),
    ('osm-standard', 'OpenStreetMap'),
    ('satellite', 'Satellite'),
    ('satellite-labels', 'Satellite + Labels'),
    ('usgs-imagery', 'USGS Imagery'),
    ('usgs-imagery-topo', 'USGS Imagery + Topo'),
    ('elevation', 'Elevation'),
    ('usgs-topo', 'USGS Topo'),
    ('esri-topo', 'Esri Topo'),
    ('opentopomap', 'OpenTopoMap'),
    ('carto-light', 'Light'),
    ('carto-dark', 'Dark'),
    ('carto-positron', 'Positron'),
    ('carto-positron-labels', 'Positron + Labels'),
    ('esri-gray', 'Gray Canvas'),
    ('carto-voyager', 'Voyager'),
    ('osm-humanitarian', 'Humanitarian'),
    ('esri-streets', 'Streets'),
    ('esri-national-geographic', 'National Geographic'),
    ('esri-oceans', 'Oceans'),
    ('osm-france', 'France Style'),
    ('openfreemap-liberty', 'OpenFreeMap Liberty'),
)

class CustomUser(AbstractUser):
    # NULL (not '') so more than one user can exist without an email.
    # PostgreSQL unique constraints treat NULL as distinct.
    email = models.EmailField(unique=True, null=True, blank=True)
    profile_pic = ResizedImageField(force_format="WEBP", quality=75, null=True, blank=True, upload_to='profile-pics/')
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    public_profile = models.BooleanField(default=False)
    disable_password = models.BooleanField(default=False)
    measurement_system = models.CharField(max_length=10, choices=[('metric', 'Metric'), ('imperial', 'Imperial')], default='metric')
    default_currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default='USD')
    date_format = models.CharField(max_length=10, choices=DATE_FORMAT_CHOICES, default='locale')
    map_style = models.CharField(max_length=32, choices=BASEMAP_CHOICES, default='default')
    legal_consent = models.JSONField(null=True, blank=True, editable=False)

    def save(self, *args, **kwargs):
        if isinstance(self.email, str) and not self.email.strip():
            self.email = None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username


class APIKey(models.Model):
    """
    Personal API keys for authenticating programmatic access.

    Security design:
    - A 32-byte cryptographically random token is generated with the prefix ``al_``.
    - Only a PBKDF2-HMAC-SHA256 derived hash of the full token is persisted;
        the plaintext is returned exactly once at creation time and never stored.
    - The first 12 characters of the token are kept as ``key_prefix`` so users can
        identify their keys without revealing the secret.
    """

    _KEY_HASH_ITERATIONS = 600000
    _KEY_HASH_SALT_NAMESPACE = "users.APIKey"
    _AUTH_CACHE_TIMEOUT = 300
    _LAST_USED_UPDATE_INTERVAL = timedelta(minutes=1)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='api_keys'
    )
    name = models.CharField(max_length=100)
    key_prefix = models.CharField(max_length=12, editable=False)
    key_hash = models.CharField(max_length=64, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} – {self.name} ({self.key_prefix}…)"

    @classmethod
    def _hash_raw_key(cls, raw_key: str) -> str:
        """Derive a computationally expensive hash for API key persistence."""
        salt = f"{cls._KEY_HASH_SALT_NAMESPACE}:{settings.SECRET_KEY}".encode("utf-8")
        return hashlib.pbkdf2_hmac(
            "sha256",
            raw_key.encode("utf-8"),
            salt,
            cls._KEY_HASH_ITERATIONS,
        ).hex()

    @classmethod
    def generate(cls, user, name: str) -> tuple['APIKey', str]:
        """
        Create a new APIKey for *user* with the given *name*.

        Returns a ``(instance, raw_key)`` tuple.  The raw key is shown to the
        user once and must never be stored anywhere after that.
        """
        raw_key = f"al_{secrets.token_urlsafe(32)}"
        key_hash = cls._hash_raw_key(raw_key)
        key_prefix = raw_key[:12]
        instance = cls.objects.create(
            user=user,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
        )
        return instance, raw_key

    @classmethod
    def authenticate(cls, raw_key: str):
        """
        Look up an APIKey by its raw value.

        Returns the matching ``APIKey`` instance (updating ``last_used_at``) or
        ``None`` if not found.
        """
        from django.core.cache import cache
        from django.utils import timezone

        # Remember verified keys so PBKDF2 doesn't run on every request. Keys are
        # 256-bit random, so a plain SHA-256 is enough for the cache key. Only the
        # pk is cached: a revoked key no longer resolves and gets the full check.
        cache_key = f"apikey:{hashlib.sha256(raw_key.encode('utf-8')).hexdigest()}"
        try:
            cached_pk = cache.get(cache_key)
        except Exception:
            cached_pk = None

        api_key = None
        if cached_pk is not None:
            api_key = cls.objects.select_related('user').filter(pk=cached_pk).first()

        if api_key is None:
            key_hash = cls._hash_raw_key(raw_key)
            try:
                api_key = cls.objects.select_related('user').get(key_hash=key_hash)
            except cls.DoesNotExist:
                return None
            try:
                cache.set(cache_key, api_key.pk, cls._AUTH_CACHE_TIMEOUT)
            except Exception:
                pass

        now = timezone.now()
        if api_key.last_used_at is None or now - api_key.last_used_at >= cls._LAST_USED_UPDATE_INTERVAL:
            cls.objects.filter(pk=api_key.pk).update(last_used_at=now)
            api_key.last_used_at = now
        return api_key