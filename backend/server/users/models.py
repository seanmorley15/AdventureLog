import hashlib
import hmac
import secrets
import uuid
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
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
    - Only a SHA-256 hash of the full token is persisted; the plaintext is returned
        exactly once at creation time and never stored. The token is 256 random bits,
        so it needs no salt or slow hash, and checking a key costs almost nothing.
    - Keys made before this scheme carry a salted PBKDF2 hash in ``key_hash``. They
        are checked the slow way once, then moved to the fast hash.
    - The first 12 characters of the token are kept as ``key_prefix`` so users can
        identify their keys without revealing the secret.
    """

    _KEY_HASH_ITERATIONS = 600000
    _KEY_HASH_SALT_NAMESPACE = "users.APIKey"
    _FAST_HASH_NAMESPACE = "adventurelog.api-key.v2:"
    # last_used_at is a hint for the key list, so it is written at most this often.
    _LAST_USED_RESOLUTION = timedelta(minutes=5)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='api_keys'
    )
    name = models.CharField(max_length=100)
    key_prefix = models.CharField(max_length=12, editable=False)
    # Legacy salted PBKDF2 hash. Empty once the key has been moved to key_hash_v2.
    key_hash = models.CharField(max_length=64, unique=True, null=True, blank=True, editable=False)
    key_hash_v2 = models.CharField(max_length=64, unique=True, null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} – {self.name} ({self.key_prefix}…)"

    @classmethod
    def _fast_hash(cls, raw_key: str) -> str:
        return hashlib.sha256((cls._FAST_HASH_NAMESPACE + raw_key).encode("utf-8")).hexdigest()

    @classmethod
    def _legacy_hash(cls, raw_key: str) -> str:
        """The expensive salted hash that keys made before the fast hash were stored under."""
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
        instance = cls.objects.create(
            user=user,
            name=name,
            key_prefix=raw_key[:12],
            key_hash_v2=cls._fast_hash(raw_key),
        )
        return instance, raw_key

    @classmethod
    def authenticate(cls, raw_key: str):
        """
        Look up an APIKey by its raw value.

        Returns the matching ``APIKey`` instance (recording when it was last used) or
        ``None`` if there is no such key or its user is deactivated.
        """
        fast_hash = cls._fast_hash(raw_key)
        api_key = cls.objects.select_related('user').filter(key_hash_v2=fast_hash).first()
        if api_key is None:
            api_key = cls._authenticate_legacy(raw_key, fast_hash)
        if api_key is None or not api_key.user.is_active:
            return None

        now = timezone.now()
        if api_key.last_used_at is None or now - api_key.last_used_at >= cls._LAST_USED_RESOLUTION:
            cls.objects.filter(pk=api_key.pk).update(last_used_at=now)
            api_key.last_used_at = now
        return api_key

    @classmethod
    def _authenticate_legacy(cls, raw_key: str, fast_hash: str):
        """
        Check a key that is still stored under the old PBKDF2 hash, and move it to the
        fast hash. The slow hash is computed only when a stored legacy key shares this
        key's 12-character prefix, so a made-up key never costs more than a lookup.
        """
        candidates = list(
            cls.objects.select_related('user').filter(key_hash_v2__isnull=True, key_prefix=raw_key[:12])
        )
        if not candidates:
            return None

        legacy_hash = cls._legacy_hash(raw_key)
        for candidate in candidates:
            if candidate.key_hash and hmac.compare_digest(candidate.key_hash, legacy_hash):
                cls.objects.filter(pk=candidate.pk).update(key_hash_v2=fast_hash, key_hash=None)
                candidate.key_hash_v2, candidate.key_hash = fast_hash, None
                return candidate
        return None