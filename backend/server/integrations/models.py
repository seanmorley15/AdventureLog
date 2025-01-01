from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ImmichIntegration(models.Model):
    server_url = models.CharField(max_length=255)
    api_key = models.CharField(max_length=255)
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.username + ' - ' + self.server_url