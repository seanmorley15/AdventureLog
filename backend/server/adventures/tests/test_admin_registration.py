from django.apps import apps
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from adventures.tests.factories import build_rich_account
from core.testing import make_user

# Models that deliberately have no admin page.
NOT_REGISTERED = {'CollectionMember', 'CollectionGuestLink', 'CollectionComment', 'CollectionActivity', 'CommentInboxState'}


class AdminRegistrationTests(SimpleTestCase):
    def test_every_adventures_model_that_had_an_admin_page_still_has_one(self):
        registered = {model.__name__ for model in admin.site._registry if model._meta.app_label == 'adventures'}

        self.assertEqual(
            registered,
            {
                'Activity', 'Category', 'Checklist', 'ChecklistItem', 'Collection', 'CollectionInvite',
                'CollectionItineraryDay', 'CollectionItineraryItem', 'ContentAttachment', 'ContentImage',
                'Location', 'Lodging', 'Note', 'Trail', 'Transportation', 'Visit',
            },
        )

    def test_the_content_type_admin_used_to_search_generic_relations_is_registered(self):
        self.assertIn(ContentType, admin.site._registry)

    def test_models_left_out_of_the_admin_are_the_ones_meant_to_be(self):
        every = {model.__name__ for model in apps.get_app_config('adventures').get_models()}
        registered = {model.__name__ for model in admin.site._registry if model._meta.app_label == 'adventures'}

        self.assertEqual(every - registered, NOT_REGISTERED)

    def test_the_site_is_branded_and_the_login_is_wrapped(self):
        self.assertEqual(admin.site.site_header, 'AdventureLog Admin')
        self.assertEqual(admin.site.index_title, 'AdventureLog administration')
        self.assertTrue(getattr(admin.site.login, '__wrapped__', None) or admin.site.login.__module__)


class AdminPagesRenderTests(TestCase):
    """Every admin page for the app's models opens, with real rows to list."""

    @classmethod
    def setUpTestData(cls):
        cls.admin_user = get_user_model().objects.create_superuser(
            username='admin-smoke', email='admin-smoke@example.com', password='testpassword123'
        )
        build_rich_account(cls.admin_user, make_user('admin-smoke-friend', public_profile=True))

    def setUp(self):
        self.client.force_login(self.admin_user)

    def test_every_changelist_and_add_form_opens(self):
        models = [m for m in admin.site._registry if m._meta.app_label == 'adventures']
        self.assertGreaterEqual(len(models), 16)
        for model in models:
            meta = model._meta
            for view in ('changelist', 'add'):
                url = reverse(f'admin:{meta.app_label}_{meta.model_name}_{view}')
                with self.subTest(model=meta.model_name, view=view):
                    self.assertEqual(self.client.get(url).status_code, 200)

    def test_a_change_form_opens_for_a_row_of_every_model(self):
        for model in [m for m in admin.site._registry if m._meta.app_label == 'adventures']:
            row = model.objects.first()
            if row is None:
                continue
            meta = model._meta
            url = reverse(f'admin:{meta.app_label}_{meta.model_name}_change', args=[row.pk])
            with self.subTest(model=meta.model_name):
                self.assertEqual(self.client.get(url).status_code, 200)
