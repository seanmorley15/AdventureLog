from datetime import datetime, timezone as tz
from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.test import override_settings

from adventures.models import Location, Notification, Visit
from adventures.services import notifications, travelers
from adventures.services.day_plan import get_day_by_index, place_object
from adventures.tests.base import AudienceTestBase
from jobs.testing import discard_pending_jobs, queued_jobs, run_pending_jobs
from django.core import mail


def at(y, m, d, hour=12):
    return datetime(y, m, d, hour, tzinfo=tz.utc)


class NotificationTestBase(AudienceTestBase):
    def _notes(self, user):
        return Notification.objects.filter(user=user)

    def _visit(self, who, when=None, location=None):
        visit = Visit.objects.create(location=location or self.hut, start_date=when or at(2026, 6, 2))
        visit.travelers.set(who)
        return visit

    def _second_stop(self):
        other = Location.objects.create(user=self.owner, name='Pier', is_public=False)
        other.collections.add(self.trip)
        place_object(
            self.trip, ContentType.objects.get_for_model(Location), other.id, day=get_day_by_index(self.trip, 1)
        )
        return other


class CreationTests(NotificationTestBase):
    def test_log_visit_notifies_the_named_collaborator_not_the_actor(self):
        self.as_user(self.editor)
        response = self.client.post(
            f'/api/collections/{self.trip.id}/itinerary-items/{self.stop.id}/log-visit/',
            {'traveler_uuids': [str(self.owner.uuid)]}, format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)
        note = self._notes(self.owner).get()
        self.assertEqual(note.kind, Notification.Kind.VISIT_TRAVELER_ADDED)
        self.assertEqual(note.actor_user, self.editor)
        self.assertEqual(note.actor_name, 'editor')
        self.assertEqual(note.data['visit_id'], response.data['visit']['id'])
        self.assertEqual(note.data['location_name'], 'Hut')
        self.assertEqual(note.data['collection_id'], str(self.trip.id))
        self.assertEqual(note.data['count'], 1)
        self.assertIsNone(note.read_at)
        self.assertFalse(self._notes(self.editor).exists())

    def test_logging_alone_notifies_nobody(self):
        self.as_user(self.editor)
        self.client.post(
            f'/api/collections/{self.trip.id}/itinerary-items/{self.stop.id}/log-visit/', {}, format='json'
        )
        self.assertFalse(Notification.objects.exists())

    def test_already_logged_path_notifies_only_the_new_people(self):
        self.as_user(self.owner)
        url = f'/api/collections/{self.trip.id}/itinerary-items/{self.stop.id}/log-visit/'
        self.client.post(url, {}, format='json')
        self.as_user(self.editor)
        self.client.post(url, {'traveler_uuids': [str(self.viewer.uuid)]}, format='json')
        self.assertEqual(self._notes(self.viewer).count(), 1)
        self.assertFalse(self._notes(self.owner).exists())  # not named, only the ones added
        self.assertFalse(self._notes(self.editor).exists())
        self.client.post(url, {'traveler_uuids': [str(self.viewer.uuid)]}, format='json')
        self.assertEqual(self._notes(self.viewer).count(), 1)  # already a traveler

    def test_visit_post_names_people(self):
        self.as_user(self.editor)
        response = self.client.post('/api/visits/', {
            'location': str(self.hut.id), 'start_date': '2026-06-02T00:00:00Z',
            'traveler_uuids': [str(self.owner.uuid), str(self.editor.uuid)],
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        # The owner is on the visit by default but was still named by someone else.
        self.assertEqual(self._notes(self.owner).count(), 1)
        self.assertFalse(self._notes(self.editor).exists())

    def test_owner_creating_a_visit_gets_no_notification_for_the_default(self):
        self.as_user(self.owner)
        self.client.post('/api/visits/', {'location': str(self.hut.id), 'start_date': '2026-06-02T00:00:00Z'},
                         format='json')
        self.assertFalse(Notification.objects.exists())

    def test_visit_patch_notifies_only_people_added(self):
        visit = self._visit([self.owner, self.editor])
        self.as_user(self.editor)
        response = self.client.patch(f'/api/visits/{visit.id}/', {
            'traveler_uuids': [str(self.owner.uuid), str(self.editor.uuid), str(self.viewer.uuid)],
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self._notes(self.viewer).count(), 1)
        self.assertFalse(self._notes(self.owner).exists())

    def test_join_notifies_nobody(self):
        visit = self._visit([self.owner])
        self.as_user(self.viewer)
        self.assertEqual(self.client.post(f'/api/visits/{visit.id}/join/').status_code, 200)
        self.assertFalse(Notification.objects.exists())

    def test_leave_copies_notify_nobody(self):
        from adventures.services.location_collections import unlink_location
        from users.services.account_deletion import delete_user_account

        def copies_of(user, name):
            return Location.objects.filter(user=user, name=name).exclude(pk__in=[self.hut.pk]).count()

        # take_my_visits
        visit = self._visit([self.owner, self.editor])
        travelers.take_my_visits(self.hut, self.editor)
        self.assertEqual(copies_of(self.editor, 'Hut'), 1)
        self.assertEqual([t.pk for t in visit.travelers.all()], [self.owner.pk])
        self.assertFalse(Notification.objects.exists())

        # release_member (leaving or being removed)
        self._visit([self.owner, self.viewer], at(2026, 6, 3))
        travelers.release_member(self.trip, self.viewer, keep_copies=True)
        self.assertEqual(copies_of(self.viewer, 'Hut'), 1)
        self.assertFalse(Notification.objects.exists())

        # release_lost_access (a place leaving its trip)
        pier = self._second_stop()
        self._visit([self.owner, self.editor], at(2026, 6, 2), location=pier)
        unlink_location(pier, self.trip)
        self.assertEqual(copies_of(self.editor, 'Pier'), 1)
        self.assertFalse(Notification.objects.exists())

        # account deletion releasing co-members
        self.trip.shared_with.add(self.stranger)
        self._visit([self.owner, self.stranger], at(2026, 6, 4))
        delete_user_account(self.owner)
        self.assertEqual(copies_of(self.stranger, 'Hut'), 1)
        self.assertFalse(Notification.objects.exists())

    def test_add_travelers_sends_one_summary_per_person_with_the_count(self):
        self._visit([self.owner], at(2026, 6, 1))
        self._visit([self.owner], at(2026, 6, 2))
        self._visit([self.owner], at(2026, 6, 3), location=self._second_stop())
        self.as_user(self.owner)
        response = self.client.post(
            f'/api/collections/{self.trip.id}/add-travelers/',
            {'user_uuids': [str(self.editor.uuid), str(self.viewer.uuid), str(self.owner.uuid)]}, format='json',
        )
        self.assertEqual(response.json(), {'visits': 3, 'locations': 2})
        for user in (self.editor, self.viewer):
            note = self._notes(user).get()
            self.assertEqual(note.data['count'], 3)
            self.assertEqual(note.data['locations'], 2)
            self.assertEqual(note.data['collection_name'], 'Lofoten')
            self.assertNotIn('visit_id', note.data)
        self.assertFalse(self._notes(self.owner).exists())

    def test_add_travelers_to_one_visit_is_the_single_form(self):
        visit = self._visit([self.owner])
        self.as_user(self.owner)
        self.client.post(f'/api/collections/{self.trip.id}/add-travelers/',
                         {'user_uuids': [str(self.editor.uuid)]}, format='json')
        note = self._notes(self.editor).get()
        self.assertEqual(note.data['visit_id'], str(visit.id))
        self.assertEqual(note.data['count'], 1)

    def test_dry_run_notifies_nobody(self):
        self._visit([self.owner])
        self.as_user(self.owner)
        self.client.post(f'/api/collections/{self.trip.id}/add-travelers/?dry_run=1',
                         {'user_uuids': [str(self.editor.uuid)]}, format='json')
        self.assertFalse(Notification.objects.exists())

    def test_log_day_sends_one_notification_per_person(self):
        self._second_stop()
        self.as_user(self.editor)
        day = get_day_by_index(self.trip, 1)
        response = self.client.post(
            f'/api/collections/{self.trip.id}/days/{day.id}/log-visit/',
            {'traveler_uuids': [str(self.viewer.uuid), str(self.owner.uuid)]}, format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        for user in (self.viewer, self.owner):
            note = self._notes(user).get()
            self.assertEqual(note.data['count'], 2)
        self.assertFalse(self._notes(self.editor).exists())

    def test_same_visit_twice_in_one_batch_counts_once(self):
        visit = self._visit([self.owner])
        with notifications.batch(self.owner, self.trip):
            travelers.add_travelers(visit, [self.editor], self.owner, collection=self.trip)
            visit.travelers.remove(self.editor)
            travelers.add_travelers(visit, [self.editor], self.owner, collection=self.trip)
        self.assertEqual(self._notes(self.editor).get().data['count'], 1)

    def test_no_actor_means_no_notification(self):
        visit = self._visit([self.owner])
        travelers.add_travelers(visit, [self.editor])
        self.assertFalse(Notification.objects.exists())

    def test_failure_to_notify_does_not_break_the_visit_change(self):
        visit = self._visit([self.owner])
        self.as_user(self.owner)
        with patch.object(Notification.objects, 'create', side_effect=RuntimeError('boom')):
            response = self.client.patch(f'/api/visits/{visit.id}/', {
                'traveler_uuids': [str(self.owner.uuid), str(self.editor.uuid)],
            }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(set(visit.travelers.values_list('username', flat=True)), {'owner', 'editor'})


class EmailTests(NotificationTestBase):
    def _add_editor(self):
        visit = self._visit([self.owner])
        self.as_user(self.owner)
        self.client.patch(f'/api/visits/{visit.id}/', {
            'traveler_uuids': [str(self.owner.uuid), str(self.editor.uuid)],
        }, format='json')
        return visit

    @override_settings(SMTP_CONFIGURED=True)
    def test_one_email_job_per_recipient_with_a_link_and_no_traveler_list(self):
        visit = self._add_editor()
        self.assertEqual(queued_jobs('adventures.send_traveler_added_email').count(), 1)
        run_pending_jobs()
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ['editor@example.com'])
        self.assertIn('owner', message.body)
        self.assertIn('Hut', message.body)
        self.assertIn(f'/locations/{self.hut.id}', message.body)
        self.assertIn('remove yourself', message.body)
        self.assertNotIn('viewer', message.body)
        self.assertTrue(visit.pk)

    @override_settings(SMTP_CONFIGURED=True)
    def test_a_failure_to_queue_the_email_keeps_the_notification(self):
        with patch('adventures.tasks.send_traveler_added_email_task.defer', side_effect=RuntimeError('queue down')):
            self._add_editor()
        self.assertEqual(self._notes(self.editor).count(), 1)

    @override_settings(SMTP_CONFIGURED=True)
    def test_line_breaks_in_a_place_name_do_not_break_the_subject(self):
        self.hut.name = 'Hut\r\nBcc: someone@example.com'
        self.hut.save()
        self._add_editor()
        run_pending_jobs()
        self.assertEqual(len(mail.outbox), 1)
        subject = mail.outbox[0].subject
        self.assertNotIn('\n', subject)
        self.assertNotIn('\r', subject)
        self.assertIn('Hut', subject)

    @override_settings(SMTP_CONFIGURED=False)
    def test_no_email_without_smtp(self):
        self._add_editor()
        self.assertEqual(queued_jobs().count(), 0)
        self.assertEqual(Notification.objects.count(), 1)

    @override_settings(SMTP_CONFIGURED=True)
    def test_no_email_without_an_address(self):
        self.editor.email = ''
        self.editor.save()
        self._add_editor()
        self.assertEqual(queued_jobs().count(), 0)
        self.assertEqual(Notification.objects.count(), 1)

    @override_settings(SMTP_CONFIGURED=True)
    def test_summary_email_names_the_trip_and_count(self):
        self._visit([self.owner], at(2026, 6, 1))
        self._visit([self.owner], at(2026, 6, 2))
        self.as_user(self.owner)
        self.client.post(f'/api/collections/{self.trip.id}/add-travelers/',
                         {'user_uuids': [str(self.editor.uuid)]}, format='json')
        self.assertEqual(queued_jobs('adventures.send_traveler_added_email').count(), 1)
        run_pending_jobs()
        self.assertIn('2 visits', mail.outbox[0].body)
        self.assertIn('Lofoten', mail.outbox[0].body)

    @override_settings(SMTP_CONFIGURED=True)
    def test_a_deleted_notification_is_skipped(self):
        self._add_editor()
        Notification.objects.all().delete()
        run_pending_jobs()
        self.assertEqual(len(mail.outbox), 0)
        discard_pending_jobs()


class ApiTests(NotificationTestBase):
    def _add(self, who=None):
        visit = self._visit([self.owner])
        self.as_user(self.owner)
        self.client.patch(f'/api/visits/{visit.id}/', {
            'traveler_uuids': [str(self.owner.uuid), *[str(u.uuid) for u in (who or [self.editor])]],
        }, format='json')
        return visit

    def test_list_newest_first_with_unread_count_and_filter(self):
        first = self._add()
        second = self._visit([self.owner], at(2026, 6, 3))
        self.client.patch(f'/api/visits/{second.id}/', {
            'traveler_uuids': [str(self.owner.uuid), str(self.editor.uuid)]}, format='json')
        self.as_user(self.editor)
        body = self.client.get('/api/notifications/').json()
        self.assertEqual(body['unread_count'], 2)
        self.assertEqual(body['count'], 2)
        self.assertEqual([r['visit_id'] for r in body['results']], [str(second.id), str(first.id)])
        row = body['results'][0]
        self.assertEqual(row['actor']['name'], 'owner')
        self.assertEqual(row['location_name'], 'Hut')
        self.assertFalse(row['read'])
        self.assertEqual(self.client.get('/api/notifications/?unread=1').json()['count'], 2)

    def test_mark_read_all_and_by_id(self):
        self._add()
        second = self._visit([self.owner], at(2026, 6, 3))
        self.client.patch(f'/api/visits/{second.id}/', {
            'traveler_uuids': [str(self.owner.uuid), str(self.editor.uuid)]}, format='json')
        self.as_user(self.editor)
        one = self._notes(self.editor).first()
        response = self.client.post('/api/notifications/mark-read/', {'ids': [str(one.id)]}, format='json')
        self.assertEqual(response.json(), {'unread_count': 1})
        self.assertEqual(self.client.get('/api/notifications/?unread=1').json()['count'], 1)
        self.assertEqual(self.client.post('/api/notifications/mark-read/', {}, format='json').json(),
                         {'unread_count': 0})
        self.assertEqual(self.client.get('/api/notifications/?unread=1').json()['count'], 0)

    def test_only_the_recipient_reads_or_marks(self):
        self._add()
        note = self._notes(self.editor).get()
        self.as_user(self.viewer)
        self.assertEqual(self.client.get('/api/notifications/').json()['count'], 0)
        self.client.post('/api/notifications/mark-read/', {'ids': [str(note.id)]}, format='json')
        note.refresh_from_db()
        self.assertIsNone(note.read_at)
        self.as_user(self.owner)  # the actor does not see it either
        self.assertEqual(self.client.get('/api/notifications/').json()['count'], 0)

    def test_anonymous_is_refused(self):
        self.as_anonymous()
        self.assertIn(self.client.get('/api/notifications/').status_code, (401, 403))
        self.assertIn(self.client.post('/api/notifications/mark-read/', {}, format='json').status_code, (401, 403))

    def test_bad_ids_are_a_400(self):
        self.as_user(self.editor)
        response = self.client.post('/api/notifications/mark-read/', {'ids': ['nope']}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_place_name_hidden_after_losing_access(self):
        self._add()
        self.trip.shared_with.remove(self.editor)
        self.as_user(self.editor)
        row = self.client.get('/api/notifications/').json()['results'][0]
        self.assertEqual(row['location_name'], '')
        self.assertIsNone(row['location_id'])
        self.assertEqual(row['collection_name'], '')

    def test_account_unread_count_includes_notifications(self):
        self._add()
        self.as_user(self.editor)
        body = self.client.get('/api/account/').json()
        self.assertEqual(body['unread_notification_count'], 1)
        self.client.post('/api/notifications/mark-read/', {}, format='json')
        self.assertEqual(self.client.get('/api/account/').json()['unread_notification_count'], 0)

    def test_a_guest_link_naming_a_member_notifies_them_as_someone_and_never_the_guest(self):
        from adventures.models import CollectionGuestLink

        link = CollectionGuestLink.objects.create(collection=self.trip, role='editor', label='Camp friend')
        self.as_anonymous()
        response = self.client.post(
            f'/api/collections/{self.trip.id}/itinerary-items/{self.stop.id}/log-visit/',
            {'traveler_uuids': [str(self.editor.uuid)]}, format='json', HTTP_X_GUEST_TOKEN=link.token,
        )
        self.assertEqual(response.status_code, 201, response.data)
        note = self._notes(self.editor).get()
        self.assertIsNone(note.actor_user)
        # A guest link has no account and the log-visit endpoints hand over no request, so nobody is named.
        self.assertEqual(note.actor_name, '')
        self.assertEqual(Notification.objects.count(), 1)  # the guest is not a person, and the owner default is silent
        self.as_user(self.editor)
        row = self.client.get('/api/notifications/').json()['results'][0]
        self.assertEqual(row['actor']['name'], '')
        self.assertIsNone(row['actor']['uuid'])
        with override_settings(SMTP_CONFIGURED=True):
            notifications.send_traveler_added_email(note)
        self.assertTrue(mail.outbox[-1].body.startswith('Someone added you'))
