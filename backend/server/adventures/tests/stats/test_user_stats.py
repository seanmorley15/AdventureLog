from datetime import timedelta

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from adventures.models import Activity, Collection, Location, Visit
from adventures.services.user_stats import UserStatsService
from adventures.utils.get_is_visited import is_location_visited
from adventures.utils.sports_types import SPORT_CATEGORIES
from users.models import CustomUser


class VisitedLocationCountTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='stats-user', email='stats-user@example.com', password='testpassword123'
        )
        self.other = CustomUser.objects.create_user(
            username='stats-other', email='stats-other@example.com', password='testpassword123'
        )
        self.now = timezone.now()

    def place(self, name, user=None, **visits):
        location = Location.objects.create(user=user or self.user, name=name)
        for visit in visits.get('visits', []):
            Visit.objects.create(location=location, **visit)
        return location

    def test_count_matches_the_per_location_rule_for_edge_cases(self):
        midnight_today = self.now.replace(hour=0, minute=0, second=0, microsecond=0)
        self.place('past', visits=[{'start_date': self.now - timedelta(days=30), 'end_date': self.now - timedelta(days=29)}])
        self.place('past, open ended', visits=[{'start_date': self.now - timedelta(days=3)}])
        self.place('started earlier today', visits=[{'start_date': midnight_today}])
        self.place('starts later today', visits=[{'start_date': midnight_today + timedelta(hours=23, minutes=59)}])
        self.place('tomorrow', visits=[{'start_date': midnight_today + timedelta(days=1)}])
        self.place('future', visits=[{'start_date': self.now + timedelta(days=40), 'end_date': self.now + timedelta(days=41)}])
        self.place('no dates', visits=[{}])
        self.place('end date only', visits=[{'end_date': self.now - timedelta(days=5)}])
        self.place('no visits')
        self.place('two visits, one counts', visits=[
            {'start_date': self.now - timedelta(days=9)},
            {'start_date': self.now - timedelta(days=2)},
        ])
        self.place('someone elses', user=self.other, visits=[{'start_date': self.now - timedelta(days=9)}])

        expected = sum(
            1 for location in Location.objects.filter(user=self.user).prefetch_related('visits')
            if is_location_visited(location)
        )

        self.assertEqual(UserStatsService().get_visited_locations_count(self.user), expected)
        self.assertEqual(expected, 5)

    def test_counting_visited_places_is_one_query(self):
        for index in range(5):
            self.place(f'place {index}', visits=[{'start_date': self.now - timedelta(days=index + 1)}])

        with CaptureQueriesContext(connection) as queries:
            UserStatsService().get_visited_locations_count(self.user)

        self.assertEqual(len(queries), 1)


class ActivityStatsTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='act-user', email='act-user@example.com', password='testpassword123'
        )
        self.trip = Collection.objects.create(user=self.user, name='Trip')
        self.service = UserStatsService()
        start = timezone.now()
        rows = [
            # sport, distance, elevation gain, moving seconds, calories, max speed
            ('Run', 5000.0, 50.0, 1500, 400.0, 4.5),
            ('Run', 10000.0, 120.0, 3300, 800.0, 5.5),
            ('TrailRun', 8000.0, 400.0, 3000, None, 4.0),
            ('Hike', 12000.0, 700.0, 14400, 900.0, 2.0),
            ('Ride', 40000.0, 300.0, 5400, 1200.0, 14.0),
        ]
        self.activities = []
        for index, (sport, distance, gain, seconds, calories, max_speed) in enumerate(rows):
            self.activities.append(Activity.objects.create(
                user=self.user, collection=self.trip, name=f'{sport} {index}', sport_type=sport,
                distance=distance, elevation_gain=gain, elevation_loss=gain / 2,
                moving_time=timedelta(seconds=seconds), calories=calories, max_speed=max_speed,
                average_speed=max_speed / 2, start_date=start - timedelta(days=index),
            ))

    def stats(self):
        return self.service.get_activity_stats_by_category(
            Activity.objects.filter(user=self.user), self.user, self.user
        )

    def test_only_categories_with_activities_appear(self):
        self.assertEqual(set(self.stats()), {'running', 'walking_hiking', 'cycling'})

    def test_category_numbers_match_a_plain_python_sum(self):
        stats = self.stats()
        for category, sports in SPORT_CATEGORIES.items():
            rows = [a for a in self.activities if a.sport_type in sports]
            if not rows:
                continue
            entry = stats[category]
            self.assertEqual(entry['count'], len(rows), category)
            self.assertEqual(entry['total_distance'], round(sum(a.distance for a in rows), 2), category)
            self.assertEqual(entry['max_distance'], round(max(a.distance for a in rows), 2), category)
            self.assertEqual(entry['total_moving_time'], int(sum(a.moving_time.total_seconds() for a in rows)), category)
            self.assertEqual(entry['total_elevation_gain'], round(sum(a.elevation_gain for a in rows), 2), category)
            self.assertEqual(entry['avg_distance'], round(sum(a.distance for a in rows) / len(rows), 2), category)
            calories = [a.calories for a in rows if a.calories is not None]
            self.assertEqual(entry['total_calories'], round(sum(calories), 2), category)
            self.assertEqual(entry['record_holders']['max_calories']['metric_value'], round(max(calories), 2), category)
            self.assertEqual(
                entry['record_holders']['max_distance']['activity_id'],
                str(max(rows, key=lambda a: a.distance).id),
                category,
            )

    def test_sport_breakdown_lists_each_sport_that_was_done(self):
        running = self.stats()['running']['sports']

        self.assertEqual(list(running), ['Run', 'TrailRun'])
        self.assertEqual(running['Run'], {'count': 2, 'total_distance': 15000.0, 'total_elevation_gain': 170.0})
        self.assertEqual(running['TrailRun'], {'count': 1, 'total_distance': 8000.0, 'total_elevation_gain': 400.0})

    def test_overall_numbers_and_record_holders(self):
        overall = self.service.get_overall_activity_stats(
            Activity.objects.filter(user=self.user), self.user, self.user
        )

        self.assertEqual(overall['total_count'], 5)
        self.assertEqual(overall['total_distance'], 75000.0)
        self.assertEqual(overall['total_calories'], 3300.0)
        holders = overall['record_holders']
        self.assertEqual(holders['max_distance']['metric_value'], 40000.0)
        self.assertEqual(holders['max_speed']['metric_value'], 14.0)
        self.assertEqual(holders['max_elevation_gain']['metric_value'], 700.0)
        self.assertEqual(holders['max_calories']['metric_value'], 1200.0)
        self.assertEqual(holders['max_distance']['sport_type'], 'Ride')

    def test_no_activities_gives_the_empty_shape(self):
        Activity.objects.all().delete()

        overall = self.service.get_overall_activity_stats(
            Activity.objects.filter(user=self.user), self.user, self.user
        )

        self.assertEqual(overall['total_count'], 0)
        self.assertEqual(overall['record_holders']['max_distance'], None)
        self.assertEqual(self.stats(), {})

    def test_stats_use_a_fixed_small_number_of_queries(self):
        with CaptureQueriesContext(connection) as category_queries:
            self.stats()
        with CaptureQueriesContext(connection) as overall_queries:
            self.service.get_overall_activity_stats(Activity.objects.filter(user=self.user), self.user, self.user)

        # 3 active categories: 1 lookup + (aggregate, per-sport, 4 record holders) each.
        self.assertLessEqual(len(category_queries), 1 + 3 * 6)
        self.assertLessEqual(len(overall_queries), 5)
