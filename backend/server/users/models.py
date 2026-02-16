import uuid
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

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)  # Override the email field with unique constraint
    profile_pic = ResizedImageField(force_format="WEBP", quality=75, null=True, blank=True, upload_to='profile-pics/')
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    public_profile = models.BooleanField(default=True)
    disable_password = models.BooleanField(default=False)
    measurement_system = models.CharField(max_length=10, choices=[('metric', 'Metric'), ('imperial', 'Imperial')], default='metric')
    default_currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default='USD')
    
    
    def __str__(self):
        return self.username