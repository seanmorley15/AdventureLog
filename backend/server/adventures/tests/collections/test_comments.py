import io
import json
import zipfile

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from adventures.models import Activity, Collection, CollectionComment, CollectionGuestLink
from adventures.tests.base import AudienceTestBase, make_user
from adventures.tests.day_plan.base import plan_request
from adventures.access.audience import resolve_audience

COMMENTS = '/api/comments/'


class CommentTestBase(AudienceTestBase):
    def thread_url(self):
        return f'/api/collections/{self.trip.id}/comments/'

    def post(self, thread='plan', body='Looks good', headers=None, **extra):
        return self.client.post(
            self.thread_url(),
            {'thread': thread, 'body': body, **extra},
            format='json',
            **(headers or {}),
        )

    def thread(self, thread='plan', **headers):
        return self.client.get(self.thread_url(), {'thread': thread}, **headers)


class PlanCommentTests(CommentTestBase):
    def test_new_collection_has_comments_off(self):
        self.assertEqual(Collection.objects.create(user=self.owner, name='New').comment_access, 'off')

    def test_editor_comments_and_viewer_reads_only(self):
        self.as_user(self.editor)
        response = self.post(body='Can we leave earlier?')
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()['author']['name'], 'editor')

        self.as_user(self.viewer)
        self.assertEqual(self.post().status_code, 403)
        listed = self.thread()
        self.assertEqual(listed.status_code, 200)
        self.assertFalse(listed.json()['can_post'])
        self.assertEqual(len(listed.json()['comments']), 1)

        self.as_user(self.stranger)
        self.assertEqual(self.thread().status_code, 404)
        self.assertEqual(self.post().status_code, 404)

    def test_guest_editor_comments_as_the_link_and_guest_viewer_cannot(self):
        editor_link = CollectionGuestLink.objects.create(collection=self.trip, role='editor', label='Family')
        viewer_link = CollectionGuestLink.objects.create(collection=self.trip, role='viewer')
        self.as_anonymous()
        response = self.post(headers={'HTTP_X_GUEST_TOKEN': editor_link.token})
        self.assertEqual(response.status_code, 201, response.content)
        comment = CollectionComment.objects.get()
        self.assertEqual((comment.author_guest_id, comment.author_name), (editor_link.pk, 'Family'))
        self.assertEqual(self.post(headers={'HTTP_X_GUEST_TOKEN': viewer_link.token}).status_code, 403)
        self.assertEqual(self.post().status_code, 404)

    def test_replies_are_one_level_and_day_comes_from_the_day(self):
        self.as_user(self.owner)
        day = self.trip.itinerary_days.get(index=2)
        root = self.post(body='Day 2 plan?', day=str(day.id)).json()
        reply = self.post(body='Yes', parent=root['id']).json()
        nested = self.post(body='Agreed', parent=reply['id']).json()
        self.assertEqual(nested['parent'], root['id'])
        self.assertEqual(nested['day_index'], 2)
        listed = self.thread().json()['comments']
        self.assertEqual(len(listed), 1)
        self.assertEqual([r['body'] for r in listed[0]['replies']], ['Yes', 'Agreed'])

    def test_edit_own_delete_own_and_owner_moderates(self):
        self.as_user(self.editor)
        comment = self.post(body='Typo').json()
        self.assertEqual(self.client.patch(f'{COMMENTS}{comment["id"]}/', {'body': 'Fixed'}, format='json').status_code, 200)
        self.assertIsNotNone(CollectionComment.objects.get().edited_at)

        other = make_user('other-editor')
        self.trip.shared_with.add(other)
        self.as_user(other)
        self.assertEqual(self.client.patch(f'{COMMENTS}{comment["id"]}/', {'body': 'Mine'}, format='json').status_code, 403)
        self.assertEqual(self.client.delete(f'{COMMENTS}{comment["id"]}/').status_code, 403)

        self.as_user(self.owner)
        self.assertEqual(self.client.delete(f'{COMMENTS}{comment["id"]}/').status_code, 204)
        self.assertFalse(CollectionComment.objects.exists())

    def test_anonymous_cannot_comment_anywhere(self):
        self.as_anonymous()
        self.assertEqual(self.post().status_code, 404)

    @override_settings(SMTP_CONFIGURED=True)
    def test_mentions_match_members_only_and_email_when_smtp_is_set(self):
        self.as_user(self.owner)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.post(body='@editor and @viewer, look. @stranger too.')
        self.assertEqual(sorted(response.json()['mentions']), ['editor', 'viewer'])
        self.assertEqual(sorted(m.to[0] for m in mail.outbox), ['editor@example.com', 'viewer@example.com'])

    @override_settings(SMTP_CONFIGURED=False)
    def test_no_email_without_smtp(self):
        self.as_user(self.owner)
        with self.captureOnCommitCallbacks(execute=True):
            self.post(body='@editor hello')
        self.assertEqual(len(mail.outbox), 0)

    def test_inbox_lists_new_comments_until_seen(self):
        self.as_user(self.editor)
        self.post(body='@owner please check day 3')
        self.as_user(self.owner)
        inbox = self.client.get(f'{COMMENTS}inbox/').json()
        self.assertEqual(inbox['unread_count'], 1)
        self.assertTrue(inbox['comments'][0]['mentions_me'])
        self.client.post(f'{COMMENTS}inbox/mark-seen/')
        self.assertEqual(self.client.get(f'{COMMENTS}inbox/').json()['unread_count'], 0)
        self.as_user(self.editor)
        self.assertEqual(self.client.get(f'{COMMENTS}inbox/').json()['comments'], [])


@override_settings(ALLOW_PUBLIC_COLLECTION_LINKS=True)
class StoryCommentTests(CommentTestBase):
    def test_comment_access_needs_a_published_story(self):
        self.as_user(self.owner)
        refused = self.client.patch(f'/api/collections/{self.trip.id}/', {'comment_access': 'signed_in'}, format='json')
        self.assertEqual(refused.status_code, 400)
        self.publish('public')
        ok = self.client.patch(f'/api/collections/{self.trip.id}/', {'comment_access': 'signed_in'}, format='json')
        self.assertEqual(ok.status_code, 200, ok.content)

    def test_public_reader_cannot_comment_until_the_owner_opts_in(self):
        self.publish('public')
        reader = make_user('reader')
        self.as_user(reader)
        self.assertEqual(self.thread('story').status_code, 404)
        self.assertEqual(self.post('story').status_code, 404)

        self.trip.comment_access = 'signed_in'
        self.trip.save()
        response = self.post('story', body='Beautiful trip!')
        self.assertEqual(response.status_code, 201, response.content)

        self.as_anonymous()
        listed = self.thread('story')
        self.assertEqual(listed.status_code, 200)
        self.assertFalse(listed.json()['can_post'])
        self.assertEqual(self.post('story').status_code, 403)

    def test_story_thread_never_includes_plan_comments(self):
        self.as_user(self.owner)
        self.post('plan', body='Door code is 4411')
        self.publish('public')
        self.trip.comment_access = 'signed_in'
        self.trip.save()
        self.post('story', body='Thanks for reading')
        self.as_anonymous()
        bodies = [c['body'] for c in self.thread('story').json()['comments']]
        self.assertEqual(bodies, ['Thanks for reading'])
        self.assertEqual(self.thread('plan').status_code, 404)

    def test_link_holders_lets_guest_links_comment_on_the_story(self):
        link = CollectionGuestLink.objects.create(collection=self.trip, role='viewer', label='Grandma')
        self.publish('unlisted')
        self.trip.comment_access = 'signed_in'
        self.trip.save()
        self.as_anonymous()
        self.assertEqual(self.post('story', headers={'HTTP_X_GUEST_TOKEN': link.token}).status_code, 403)
        self.trip.comment_access = 'link_holders'
        self.trip.save()
        response = self.post('story', body='So proud', headers={'HTTP_X_GUEST_TOKEN': link.token})
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()['author']['name'], 'Grandma')

    def test_story_hides_private_author_details(self):
        hidden = make_user('hidden')
        hidden.public_profile = False
        hidden.save()
        self.publish('public')
        self.trip.comment_access = 'signed_in'
        self.trip.save()
        self.as_user(hidden)
        self.post('story', body='Hi')
        self.as_anonymous()
        author = self.thread('story').json()['comments'][0]['author']
        self.assertIsNone(author['username'])
        self.assertIsNone(author['profile_pic'])

    def test_story_response_has_no_activity_or_plan_comments(self):
        self.as_user(self.owner)
        self.post('plan', body='Private note')
        self.publish('public')
        self.as_anonymous()
        story = self.client.get(f'/api/collections/{self.trip.id}/').json()
        self.assertNotIn('activity', story)
        self.assertNotIn('comments', story)
        self.assertNotIn('Private note', json.dumps(story))
        self.assertEqual(story['comment_access'], 'off')


class ActivityTests(CommentTestBase):
    def feed(self):
        return self.client.get(f'/api/collections/{self.trip.id}/activity/')

    def test_editor_reads_the_feed_viewer_does_not(self):
        self.as_user(self.editor)
        day = self.trip.itinerary_days.get(index=1)
        plan_request(self.client, self.trip, 'days/move', {'day': str(day.id), 'position': 3})
        self.move_stop(2)
        plan_request(self.client, self.trip, 'shift', {'days': 2})
        self.post(body='Moved things around')
        verbs = [event['verb'] for event in self.feed().json()]
        self.assertEqual(verbs, ['comment_added', 'anchor_changed', 'item_moved', 'day_moved'])

        self.as_user(self.viewer)
        self.assertEqual(self.feed().status_code, 403)
        self.as_user(self.stranger)
        self.assertEqual(self.feed().status_code, 404)

    def test_membership_events_are_owner_only(self):
        self.as_user(self.owner)
        self.client.delete(f'/api/collections/{self.trip.id}/members/{self.viewer.uuid}/')
        self.assertIn('member_removed', [e['verb'] for e in self.feed().json()])
        self.as_user(self.editor)
        self.assertNotIn('member_removed', [e['verb'] for e in self.feed().json()])


class CommentBackupTests(CommentTestBase):
    def export(self):
        self.as_user(self.owner)
        response = self.client.get('/api/backup/export/')
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            return json.loads(archive.read('data.json'))

    def restore(self, data):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('data.json', json.dumps(data))
        return self.client.post(
            '/api/backup/import/',
            {'file': SimpleUploadedFile('backup.zip', buffer.getvalue(), content_type='application/zip'), 'confirm': 'yes'},
            format='multipart',
        )

    @override_settings(ALLOW_PUBLIC_COLLECTION_LINKS=True)
    def test_full_round_trip_keeps_plan_roles_story_and_comments(self):
        self.publish('public', costs=True)
        self.trip.comment_access = 'signed_in'
        self.trip.save()
        day = self.trip.itinerary_days.get(index=2)
        Activity.objects.create(user=self.owner, day=day, name='Ridge walk')
        self.as_user(self.editor)
        root = self.post(body='Day 2?', day=str(day.id)).json()
        self.post(body='Yes', parent=root['id'])
        self.as_user(self.owner)
        self.post('story', body='Welcome, readers')

        data = self.export()
        self.assertEqual(data['backup_schema'], 6)
        self.assertEqual(self.restore(data).status_code, 200)

        restored = Collection.objects.get(user=self.owner, name='Lofoten')
        self.assertEqual(restored.type, 'trip')
        self.assertEqual(restored.itinerary_days.filter(index__isnull=False).count(), 3)
        self.assertTrue(Activity.objects.filter(day__collection=restored, name='Ridge walk').exists())
        # The viewer is invited back with their role, and only reads the story until they accept.
        self.assertEqual(resolve_audience(restored, self.viewer).role, 'public')
        self.assertEqual(restored.invites.get(invited_user=self.viewer).role, 'viewer')
        self.assertEqual(restored.story_groups, {'costs': True})
        self.assertEqual(restored.comment_access, 'signed_in')
        plan = restored.comments.filter(is_story=False).order_by('created_at')
        self.assertEqual([c.body for c in plan], ['Day 2?', 'Yes'])
        self.assertEqual(plan[1].parent_id, plan[0].pk)
        self.assertEqual(plan[0].day.index, 2)
        # Written as the editor, but never linked to their account by a file.
        self.assertIsNone(plan[0].author_user)
        self.assertEqual(plan[0].author_name, 'editor')
        self.assertEqual(list(restored.comments.filter(is_story=True).values_list('body', flat=True)), ['Welcome, readers'])

    def test_restore_cannot_write_as_or_mention_other_accounts(self):
        self.trip.comment_access = 'signed_in'
        self.trip.save()
        data = self.export()
        for col in data['collections']:
            col['comments'] = [
                {
                    'export_id': 0,
                    'body': 'I never said this',
                    'is_story': False,
                    'author_user_uuid': str(self.stranger.uuid),
                    'author_name': 'stranger',
                    'mention_uuids': [str(self.stranger.uuid), str(self.owner.uuid)],
                },
                {
                    'export_id': 1,
                    'body': 'Mine',
                    'is_story': False,
                    'author_user_uuid': str(self.owner.uuid),
                    'author_name': 'owner',
                },
            ]
        self.assertEqual(self.restore(data).status_code, 200)

        restored = Collection.objects.get(user=self.owner, name='Lofoten')
        forged = restored.comments.get(body='I never said this')
        mine = restored.comments.get(body='Mine')
        self.assertIsNone(forged.author_user)
        self.assertEqual(forged.author_name, 'stranger')
        self.assertEqual(list(forged.mentions.all()), [self.owner])
        self.assertEqual(mine.author_user, self.owner)

    def test_restore_relinks_guest_comments_to_the_new_guest_link(self):
        link = CollectionGuestLink.objects.create(collection=self.trip, role='editor', label='Family')
        self.trip.comment_access = 'link_holders'
        self.trip.save()
        CollectionComment.objects.create(
            collection=self.trip, author_guest=link, author_name='Family', body='Hello from the guest link'
        )
        self.assertEqual(self.restore(self.export()).status_code, 200)

        restored = Collection.objects.get(user=self.owner, name='Lofoten')
        comment = restored.comments.get(body='Hello from the guest link')
        new_link = restored.guest_links.get()
        self.assertEqual(comment.author_guest, new_link)
        self.assertNotEqual(new_link.token, link.token)

    def test_older_backup_leaves_comments_off(self):
        data = self.export()
        data['backup_schema'] = 5
        for col in data['collections']:
            col['comment_access'] = 'signed_in'
            col['comments'] = [{'export_id': 0, 'body': 'Ghost', 'is_story': False}]
        self.assertEqual(self.restore(data).status_code, 200)
        restored = Collection.objects.get(user=self.owner, name='Lofoten')
        self.assertEqual(restored.comment_access, 'off')
        self.assertFalse(restored.comments.exists())

    def test_backup_without_schema_still_imports_and_newer_schema_is_refused(self):
        data = self.export()
        data.pop('backup_schema')
        self.assertEqual(self.restore(data).status_code, 200)
        self.assertTrue(Collection.objects.filter(user=self.owner, name='Lofoten', type='trip').exists())
        data['backup_schema'] = 7
        self.assertEqual(self.restore(data).status_code, 400)


class ProfileLinkTests(CommentTestBase):
    def test_authors_carry_profile_details_and_visibility_of_the_link(self):
        private = make_user('private-person')
        private.public_profile = False
        private.save()
        self.trip.shared_with.add(private)
        self.as_user(private)
        self.post(body='from a private profile')
        self.as_user(self.editor)
        self.post(body='from a public profile')

        author = {c['body']: c['author'] for c in self.thread().json()['comments']}
        self.assertEqual(author['from a public profile']['username'], 'editor')
        self.assertTrue(author['from a public profile']['can_view_profile'])
        # Members see who wrote it, but a private profile has no page to open.
        self.assertEqual(author['from a private profile']['username'], 'private-person')
        self.assertFalse(author['from a private profile']['can_view_profile'])

        # People always can open their own.
        self.as_user(private)
        own = {c['body']: c['author'] for c in self.thread().json()['comments']}
        self.assertTrue(own['from a private profile']['can_view_profile'])

    def test_activity_and_inbox_name_the_person(self):
        self.as_user(self.editor)
        self.post(body='hello @owner')
        self.as_user(self.owner)
        feed = self.client.get(f'/api/collections/{self.trip.id}/activity/').json()
        self.assertEqual(feed[0]['actor']['username'], 'editor')
        self.assertTrue(feed[0]['actor']['can_view_profile'])
        inbox = self.client.get(f'{COMMENTS}inbox/').json()['comments'][0]
        self.assertEqual(inbox['author']['username'], 'editor')
