import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

VALID_ACHIEVEMENT_TYPES = [
    "adventure_count",
    "country_count",
]

class Achievement(models.Model):
    """Stores all possible achievements"""
    name = models.CharField(max_length=255, unique=True)
    key = models.CharField(max_length=255, unique=True, default='achievements.other') # Used for frontend lookups, e.g. "achievements.first_adventure"
    type = models.CharField(max_length=255, choices=[(tag, tag) for tag in VALID_ACHIEVEMENT_TYPES], default='adventure_count')  # adventure_count, country_count, etc.
    description = models.TextField()
    icon = models.ImageField(upload_to="achievements/", null=True, blank=True)
    condition = models.JSONField()  # Stores rules like {"type": "adventure_count", "value": 10}

    def __str__(self):
        return self.name

class UserAchievement(models.Model):
    """Tracks which achievements a user has earned"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "achievement")  # Prevent duplicates

    def __str__(self):
        return f"{self.user.username} - {self.achievement.name}"
