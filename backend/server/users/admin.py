from django.contrib import admin
from allauth.account.decorators import secure_admin_login
from django.contrib.sessions.models import Session

admin.autodiscover()
admin.site.login = secure_admin_login(admin.site.login)

class SessionAdmin(admin.ModelAdmin):
    def _session_data(self, obj):
        return obj.get_decoded()
    list_display = ['session_key', '_session_data', 'expire_date']

admin.site.register(Session, SessionAdmin)