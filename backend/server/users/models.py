from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    profile_pic = models.ImageField(null=True, blank=True, upload_to='profile-pics/')

    def __str__(self):
        return self.username