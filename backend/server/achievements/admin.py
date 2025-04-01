from django.contrib import admin
from allauth.account.decorators import secure_admin_login
from achievements.models import Achievement, UserAchievement

admin.autodiscover()
admin.site.login = secure_admin_login(admin.site.login)

admin.site.register(Achievement)
admin.site.register(UserAchievement)