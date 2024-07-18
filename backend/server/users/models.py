from django.contrib.auth.models import AbstractUser
from django.db import models
from django_resized import ResizedImageField

class CustomUser(AbstractUser):
    profile_pic = ResizedImageField(force_format="WEBP", quality=75, null=True, blank=True, upload_to='profile-pics/')

    def __str__(self):
        return self.username