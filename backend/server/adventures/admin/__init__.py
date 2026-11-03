"""Django admin for the adventures app, one module per area. Importing them registers the models."""

from allauth.account.decorators import secure_admin_login
from django.contrib import admin

from . import collections, logistics, media, places

# Listing them makes the imports above part of the package's interface: importing a module is what registers its models.
__all__ = ['collections', 'logistics', 'media', 'places']

admin.site.login = secure_admin_login(admin.site.login)
admin.site.site_header = 'AdventureLog Admin'
admin.site.site_title = 'AdventureLog Admin'
admin.site.index_title = 'AdventureLog administration'
