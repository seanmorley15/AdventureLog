from django.test import SimpleTestCase

from adventures.services.recommendations.scoring import score_place

R = 5000


class ScoringTests(SimpleTestCase):
    def google(self, **extra):
        place = {'rating': 4.5, 'review_count': 500, 'distance_km': 1.0, 'photos': ['p'], 'opening_hours': ['x']}
        place.update(extra)
        return place

    def test_better_rating_scores_higher(self):
        self.assertGreater(score_place(self.google(rating=4.8), R), score_place(self.google(rating=3.6), R))

    def test_more_reviews_score_higher(self):
        self.assertGreater(score_place(self.google(review_count=2000), R), score_place(self.google(review_count=20), R))

    def test_few_reviews_cannot_beat_proven_place(self):
        flashy = self.google(rating=5.0, review_count=2)
        proven = self.google(rating=4.6, review_count=3000)
        self.assertGreater(score_place(proven, R), score_place(flashy, R))

    def test_closer_scores_higher_and_decays_smoothly(self):
        near, mid, far = (score_place(self.google(distance_km=d), R) for d in (0.2, 2.5, 4.9))
        self.assertGreater(near, mid)
        self.assertGreater(mid, far)

    def test_score_is_bounded(self):
        best = self.google(rating=5.0, review_count=10**6, distance_km=0, website='w', description='d')
        self.assertLessEqual(score_place(best, R), 100)
        self.assertGreaterEqual(score_place({}, R), 0)

    def test_notable_osm_place_is_competitive_with_google(self):
        osm = {'wikidata': 'Q1', 'website': 'w', 'photos': ['p'], 'opening_hours': ['x'], 'address': 'a',
               'distance_km': 1.0}
        modest_google = self.google(rating=4.0, review_count=30)
        self.assertGreater(score_place(osm, R), score_place(modest_google, R) - 15)

    def test_unnotable_osm_place_ranks_below_good_google(self):
        self.assertLess(score_place({'distance_km': 1.0}, R), score_place(self.google(), R))
