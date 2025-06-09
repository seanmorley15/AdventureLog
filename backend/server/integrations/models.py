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