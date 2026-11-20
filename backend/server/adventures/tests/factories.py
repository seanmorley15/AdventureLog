"""One account that touches every kind of record a backup carries."""

import base64
from datetime import date, datetime, time, timedelta, timezone

from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile

from adventures.models import (
    Activity, Category, Checklist, ChecklistItem, Collection, CollectionComment,
    CollectionGuestLink, CollectionItineraryDay, CollectionItineraryItem, CollectionMember,
    ContentAttachment, ContentImage, Location, Lodging, Note, Trail, Transportation, Visit,
)
from core.geo import make_point
from worldtravel.models import City, Country, Region, VisitedCity, VisitedRegion

PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
)
GPX = b"""<?xml version="1.0"?>
<gpx version="1.1"><trk><trkseg>
<trkpt lat="44.0" lon="-71.0"><ele>100</ele></trkpt>
<trkpt lat="44.1" lon="-71.1"><ele>140</ele></trkpt>
</trkseg></trk></gpx>
"""


def ensure_geography():
    country, _ = Country.objects.get_or_create(
        country_code='FR', defaults={'name': 'France', 'coordinates': make_point(2.2, 46.2)}
    )
    region, _ = Region.objects.get_or_create(id='FR-ARA', defaults={'name': 'Auvergne-Rhone-Alpes', 'country': country})
    city, _ = City.objects.get_or_create(id='FR-ARA-1', defaults={'name': 'Chamonix', 'region': region})
    return country, region, city


def _image(owner, target, name='photo.png', **extra):
    # An Immich photo is a reference, never a stored file.
    image = None if extra.get('immich_id') else ContentFile(PNG, name=name)
    return ContentImage.objects.create(user=owner, image=image, content_object=target, **extra)


def _attachment(owner, target, name, content=b'notes'):
    return ContentAttachment.objects.create(
        user=owner, file=ContentFile(content, name=f'{name}.txt'), name=name, content_object=target
    )


def build_rich_account(owner, friend):
    """Create the records; ``friend`` must have a public profile so sharing restores."""
    country, region, city = ensure_geography()
    VisitedRegion.objects.create(user=owner, region=region)
    VisitedCity.objects.create(user=owner, city=city)
    food = Category.objects.create(user=owner, name='food', display_name='Food & Drink', icon='🍜')

    trip = Collection.objects.create(
        user=owner, name='Alps', description='Summer in the Alps', type='trip',
        start_date=date(2026, 6, 1), end_date=date(2026, 6, 5), timezone='Europe/Paris',
        link='https://example.com/alps', visibility='unlisted', story_groups={'costs': True},
        comment_access='signed_in', is_archived=False,
    )
    folder = Collection.objects.create(user=owner, name='Wishlist', description='Someday')
    trip.shared_with.add(friend)
    CollectionMember.objects.filter(collection=trip, user=friend).update(role='viewer')
    guest = CollectionGuestLink.objects.create(collection=trip, role='editor', label='Family')

    days = {
        index: CollectionItineraryDay.objects.create(
            collection=trip, index=index, date=date(2026, 6, index),
            name=f'Day {index}', description=f'Notes for day {index}',
        )
        for index in range(1, 6)
    }

    hut = Location(
        user=owner, name='Refuge du Goûter', location='Saint-Gervais', tags=['hut', 'alpine'],
        description='High hut', rating=4.5, price=120, price_currency='EUR',
        link='https://example.com/hut', is_public=True, coordinates=make_point(6.85, 45.85),
        city=city, region=region, country=country, category=food,
    )
    hut.save(_skip_geocode=True)
    cafe = Location(user=owner, name='Café du Lac', coordinates=make_point(6.12, 45.9), region=region, country=country)
    cafe.save(_skip_geocode=True)
    spare = Location(user=owner, name='Spare place')
    spare.save(_skip_geocode=True)
    hut.collections.add(trip)
    cafe.collections.add(trip, folder)

    visit = Visit.objects.create(
        location=hut, start_date=datetime(2026, 6, 2, 9, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 6, 2, 17, 0, tzinfo=timezone.utc), timezone='Europe/Paris', notes='Clear skies',
    )
    Visit.objects.create(location=hut, start_date=datetime(2025, 8, 1, tzinfo=timezone.utc), notes='Earlier visit')
    trail = Trail.objects.create(
        user=owner, location=hut, name='Tête Rousse route',
        wanderer_id='w-1', wanderer_author_username='ana', wanderer_author_domain='wanderer.example',
    )
    activity = Activity(
        user=owner, visit=visit, trail=trail, name='Ascent', sport_type='Hike', distance=7200.5,
        moving_time=timedelta(hours=5), elapsed_time=timedelta(hours=6), rest_time=timedelta(minutes=30),
        elevation_gain=1600.0, elevation_loss=10.0, elev_high=3800.0, elev_low=2200.0,
        start_date=datetime(2026, 6, 2, 7, 0, tzinfo=timezone.utc),
        start_date_local=datetime(2026, 6, 2, 9, 0, tzinfo=timezone.utc), timezone='Europe/Paris',
        average_speed=1.2, max_speed=2.5, average_cadence=80.0, calories=2100.0,
        start_point=make_point(6.85, 45.85), end_point=make_point(6.86, 45.86), external_service_id='ext-9',
    )
    activity.gpx_file.save('ascent.gpx', ContentFile(GPX), save=False)
    activity.save()

    _image(owner, trail, 'trail.png')
    _image(owner, activity, 'ascent.png')
    hut_photo = _image(owner, hut, 'hut.png', is_primary=True)
    _image(owner, hut, 'hut-2.png')
    _image(owner, visit, 'visit.png')
    _image(owner, hut, 'remote.png', immich_id='immich-1', source='immich')
    _attachment(owner, hut, 'Reservation')
    _attachment(owner, visit, 'Visit log')
    trip.primary_image = hut_photo
    trip.save(update_fields=['primary_image'])

    train = Transportation.objects.create(
        user=owner, collection=trip, type='train', name='TGV to Annecy', description='Paris to Annecy',
        rating=4.0, price=89, price_currency='EUR', link='https://example.com/tgv',
        date=datetime(2026, 6, 1, 7, 0, tzinfo=timezone.utc), end_date=datetime(2026, 6, 1, 10, 30, tzinfo=timezone.utc),
        start_timezone='Europe/Paris', end_timezone='Europe/Paris', flight_number=None,
        from_location='Paris', to_location='Annecy', start_code='PAR', end_code='NCY', origin=make_point(2.37, 48.84),
        destination=make_point(6.12, 45.9), is_public=True,
    )
    _image(owner, train, 'ticket.png')
    _attachment(owner, train, 'Ticket')
    inn = Lodging.objects.create(
        user=owner, collection=trip, name='Chalet Mont-Blanc', type='cabin', description='Cosy',
        rating=5.0, link='https://example.com/chalet', check_in=datetime(2026, 6, 2, 15, 0, tzinfo=timezone.utc),
        check_out=datetime(2026, 6, 4, 10, 0, tzinfo=timezone.utc), timezone='Europe/Paris',
        reservation_number='CH-77', price=0, price_currency='EUR', coordinates=make_point(6.87, 45.92),
        location='Chamonix', is_public=False,
    )
    _image(owner, inn, 'chalet.png')
    _attachment(owner, inn, 'Booking')
    packing = Note.objects.create(
        user=owner, collection=trip, name='Packing', content='Layers', links=['https://example.com/gear'],
        date=date(2026, 5, 30), is_public=False, is_private=True,
    )
    _image(owner, packing, 'note.png')
    loose_note = Note.objects.create(user=owner, name='Loose note', content='No collection')
    todo = Checklist.objects.create(user=owner, collection=trip, name='Before leaving', date=date(2026, 5, 31))
    ChecklistItem.objects.create(user=owner, checklist=todo, name='Passport', is_checked=True)
    ChecklistItem.objects.create(user=owner, checklist=todo, name='Gift', is_checked=False, is_private=True)

    def place(item, day=None, order=0, **extra):
        ctype = ContentType.objects.get_for_model(type(item))
        return CollectionItineraryItem.objects.create(
            collection=trip, content_type=ctype, object_id=item.id, day=day,
            date=day.date if day else None, order=order, **extra,
        )

    place(train, days[1], 0, start_time=time(7, 0), end_time=time(10, 30), timezone='Europe/Paris')
    hut_row = place(hut, days[2], 0, logged_visit=visit, is_optional=True)
    place(inn, days[2], 1, span_end_index=4)
    place(cafe, days[3], 0)
    place(packing, None, 0, is_global=True)
    place(todo, None, 1, is_global=True)

    day_trail = Trail.objects.create(user=owner, day=days[3], name='Lake loop', link='https://example.com/loop', span_end_index=4)
    _image(owner, day_trail, 'loop.png')
    day_activity = Activity(
        user=owner, day=days[3], trail=day_trail, name='Morning run', sport_type='Run', distance=5000.0,
        elevation_loss=0.0, calories=0.0, moving_time=timedelta(0), external_service_id='strava-7',
        start_point=make_point(6.12, 45.9), end_point=make_point(6.13, 45.91),
    )
    day_activity.gpx_file.save('run.gpx', ContentFile(GPX), save=False)
    day_activity.save()
    _image(owner, days[3], 'day3.png')
    _image(owner, trip, 'ideas.png')
    idea_trail = Trail.objects.create(user=owner, collection=trip, name='Someday ridge', link='https://example.com/ridge')

    thread = CollectionComment.objects.create(collection=trip, author_user=owner, author_name='Owner', body='Plan looks good')
    reply = CollectionComment.objects.create(
        collection=trip, parent=thread, author_user=friend, author_name='Friend', body='Agreed', day=days[2],
    )
    reply.mentions.add(owner)
    CollectionComment.objects.create(
        collection=trip, author_user=owner, author_name='Owner', body='Book the hut early', placement=hut_row,
    )
    CollectionComment.objects.create(collection=trip, is_story=True, author_guest=guest, author_name='Family', body='Lovely story')

    return {
        'trip': trip, 'folder': folder, 'hut': hut, 'cafe': cafe, 'spare': spare, 'visit': visit,
        'train': train, 'inn': inn, 'packing': packing, 'loose_note': loose_note, 'todo': todo,
        'days': days, 'hut_row': hut_row, 'guest': guest, 'day_trail': day_trail,
        'idea_trail': idea_trail, 'country': country, 'region': region, 'city': city,
    }
