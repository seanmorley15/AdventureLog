from rest_framework.test import APITestCase

from adventures.models import Checklist, ChecklistItem
from users.models import CustomUser


class ChecklistItemSyncTests(APITestCase):
    """Saving a checklist keeps its items (#1305)."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='packer', email='packer@example.com', password='testpassword'
        )
        self.client.force_authenticate(self.user)
        response = self.client.post('/api/checklists/', {
            'name': 'Packing',
            'items': [{'name': 'Passport'}, {'name': 'Charger'}],
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.checklist_id = response.json()['id']
        self.items = {item['name']: item for item in response.json()['items']}

    def url(self):
        return f'/api/checklists/{self.checklist_id}/'

    def stored(self):
        return {item.name: item for item in ChecklistItem.objects.filter(checklist_id=self.checklist_id)}

    def test_ticking_an_item_keeps_every_item(self):
        passport, charger = self.items['Passport'], self.items['Charger']
        response = self.client.patch(self.url(), {
            'items': [{**passport, 'is_checked': True}, charger],
        }, format='json')

        self.assertEqual(response.status_code, 200)
        stored = self.stored()
        self.assertEqual(str(stored['Passport'].id), passport['id'])
        self.assertEqual(str(stored['Charger'].id), charger['id'])
        self.assertTrue(stored['Passport'].is_checked)
        self.assertFalse(stored['Charger'].is_checked)

    def test_a_patch_without_items_leaves_them_alone(self):
        response = self.client.patch(self.url(), {'name': 'Carry-on'}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Checklist.objects.get(id=self.checklist_id).name, 'Carry-on')
        self.assertEqual(set(self.stored()), {'Passport', 'Charger'})

    def test_items_are_added_and_removed(self):
        response = self.client.patch(self.url(), {
            'items': [self.items['Passport'], {'name': 'Adapter'}],
        }, format='json')

        self.assertEqual(response.status_code, 200)
        stored = self.stored()
        self.assertEqual(set(stored), {'Passport', 'Adapter'})
        self.assertEqual(str(stored['Passport'].id), self.items['Passport']['id'])
        self.assertEqual(stored['Adapter'].user, self.user)

    def test_an_item_of_another_checklist_is_never_taken_over(self):
        other = Checklist.objects.create(user=self.user, name='Groceries')
        milk = ChecklistItem.objects.create(checklist=other, user=self.user, name='Milk')

        response = self.client.patch(self.url(), {
            'items': [{'id': str(milk.id), 'name': 'Milk', 'is_checked': True}],
        }, format='json')

        self.assertEqual(response.status_code, 200)
        milk.refresh_from_db()
        self.assertEqual(milk.checklist, other)
        self.assertFalse(milk.is_checked)
        stored = self.stored()
        self.assertEqual(set(stored), {'Milk'})
        self.assertNotEqual(stored['Milk'].id, milk.id)
