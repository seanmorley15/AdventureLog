from rest_framework.test import APITestCase

from adventures.models import ChecklistItem
from users.models import CustomUser


class ChecklistItemUpdateTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='checklist-owner',
            email='checklist-owner@example.com',
            password='testpassword123',
        )
        self.client.force_authenticate(user=self.user)

    def test_update_keeps_existing_item_ids(self):
        created = self.client.post('/api/checklists/', {
            'name': 'Packing',
            'items': [{'name': 'Passport'}, {'name': 'Charger'}],
        }, format='json')
        self.assertEqual(created.status_code, 201)
        items = created.data['items']
        original_ids = {item['id'] for item in items}

        items[0]['is_checked'] = True
        updated = self.client.patch(
            f"/api/checklists/{created.data['id']}/",
            {'items': items + [{'name': 'Adapter'}]},
            format='json',
        )
        self.assertEqual(updated.status_code, 200)

        updated_ids = {item['id'] for item in updated.data['items']}
        self.assertTrue(original_ids < updated_ids)
        self.assertEqual(len(updated_ids), 3)
        self.assertTrue(ChecklistItem.objects.get(id=items[0]['id']).is_checked)

    def test_unknown_item_id_creates_new_item(self):
        created = self.client.post('/api/checklists/', {'name': 'Packing', 'items': []}, format='json')
        unknown_id = '00000000-0000-0000-0000-000000000001'
        updated = self.client.patch(
            f"/api/checklists/{created.data['id']}/",
            {'items': [{'id': unknown_id, 'name': 'Tickets'}]},
            format='json',
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(len(updated.data['items']), 1)
        self.assertNotEqual(updated.data['items'][0]['id'], unknown_id)

    def test_blank_item_id_creates_new_item(self):
        created = self.client.post('/api/checklists/', {
            'name': 'Packing',
            'items': [{'id': '', 'name': 'Passport', 'is_checked': False}],
        }, format='json')
        self.assertEqual(created.status_code, 201)
        items = created.data['items']

        updated = self.client.patch(
            f"/api/checklists/{created.data['id']}/",
            {'items': items + [{'id': '', 'name': 'Charger', 'is_checked': False}]},
            format='json',
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(len(updated.data['items']), 2)
        self.assertIn(items[0]['id'], {item['id'] for item in updated.data['items']})
