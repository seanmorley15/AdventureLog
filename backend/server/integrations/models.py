from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class ImmichIntegration(models.Model):
    server_url = models.CharField(max_length=255)
    api_key = models.CharField(max_length=255)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE)
    copy_locally = models.BooleanField(default=True, help_text="Copy image to local storage, instead of just linking to the remote URL.")
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)

    def __str__(self):
        return self.user.username + ' - ' + self.server_url
    
class StravaToken(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='strava_tokens')
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255)
    expires_at = models.BigIntegerField()  # Unix timestamp
    athlete_id = models.BigIntegerField(null=True, blank=True)
    scope = models.CharField(max_length=255, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

class WandererIntegration(models.Model):
    server_url = models.CharField(max_length=255)
    username = models.CharField(max_length=255)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='wanderer_integrations')
    token = models.CharField(null=True, blank=True)
    token_expiry = models.DateTimeField(null=True, blank=True)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)

    def __str__(self):
        return self.user.username + ' - ' + self.server_url
    
    class Meta:
        verbose_name = "Wanderer Integration"
        verbose_name_plural = "Wanderer Integrations"