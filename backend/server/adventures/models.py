from django.core.exceptions import ValidationError
import os
from typing import Iterable
import uuid
from django.db import models
from django.utils.deconstruct import deconstructible
from adventures.managers import AdventureManager
import threading
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.forms import ValidationError
from django_resized import ResizedImageField
from worldtravel.models import City, Country, Region, VisitedCity, VisitedRegion
from django.core.exceptions import ValidationError
from django.utils import timezone

def background_geocode_and_assign(adventure_id: str):
    print(f"[Adventure Geocode Thread] Starting geocode for adventure {adventure_id}")
    try:
        adventure = Adventure.objects.get(id=adventure_id)
        if not (adventure.latitude and adventure.longitude):
            return
        
        from adventures.geocoding import reverse_geocode  # or wherever you defined it
        is_visited = adventure.is_visited_status()
        result = reverse_geocode(adventure.latitude, adventure.longitude, adventure.user_id)

        if 'region_id' in result:
            region = Region.objects.filter(id=result['region_id']).first()
            if region:
                adventure.region = region
                if is_visited:
                    VisitedRegion.objects.get_or_create(user_id=adventure.user_id, region=region)

        if 'city_id' in result:
            city = City.objects.filter(id=result['city_id']).first()
            if city:
                adventure.city = city
                if is_visited:
                    VisitedCity.objects.get_or_create(user_id=adventure.user_id, city=city)

        if 'country_id' in result:
            country = Country.objects.filter(country_code=result['country_id']).first()
            if country:
                adventure.country = country

        # Save updated location info
        # Save updated location info, skip geocode threading
        adventure.save(update_fields=["region", "city", "country"], _skip_geocode=True)

        # print(f"[Adventure Geocode Thread] Successfully processed {adventure_id}: {adventure.name} - {adventure.latitude}, {adventure.longitude}")

    except Exception as e:
        # Optional: log or print the error
        print(f"[Adventure Geocode Thread] Error processing {adventure_id}: {e}")

def validate_file_extension(value):
    import os
    from django.core.exceptions import ValidationError
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp4', '.mov', '.avi', '.mkv', '.mp3', '.wav', '.flac', '.ogg', '.m4a', '.wma', '.aac', '.opus', '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.zst', '.lz4', '.lzma', '.lzo', '.z', '.tar.gz', '.tar.bz2', '.tar.xz', '.tar.zst', '.tar.lz4', '.tar.lzma', '.tar.lzo', '.tar.z', '.gpx', '.md']
    if not ext.lower() in valid_extensions:
        raise ValidationError('Unsupported file extension.')

ADVENTURE_TYPES = [
    ('general', 'General 🌍'),
    ('outdoor', 'Outdoor 🏞️'),
    ('lodging', 'Lodging 🛌'),
    ('dining', 'Dining 🍽️'),
    ('activity', 'Activity 🏄'),
    ('attraction', 'Attraction 🎢'),
    ('shopping', 'Shopping 🛍️'),
    ('nightlife', 'Nightlife 🌃'),
    ('event', 'Event 🎉'),
    ('transportation', 'Transportation 🚗'),
    ('culture', 'Culture 🎭'),
    ('water_sports', 'Water Sports 🚤'),
    ('hiking', 'Hiking 🥾'),
    ('wildlife', 'Wildlife 🦒'),
    ('historical_sites', 'Historical Sites 🏛️'),
    ('music_concerts', 'Music & Concerts 🎶'),
    ('fitness', 'Fitness 🏋️'),
    ('art_museums', 'Art & Museums 🎨'),
    ('festivals', 'Festivals 🎪'),
    ('spiritual_journeys', 'Spiritual Journeys 🧘‍♀️'),
    ('volunteer_work', 'Volunteer Work 🤝'),
    ('other', 'Other')
]

TIMEZONES = [
  "Africa/Abidjan",
  "Africa/Accra",
  "Africa/Addis_Ababa",
  "Africa/Algiers",
  "Africa/Asmera",
  "Africa/Bamako",
  "Africa/Bangui",
  "Africa/Banjul",
  "Africa/Bissau",
  "Africa/Blantyre",
  "Africa/Brazzaville",
  "Africa/Bujumbura",
  "Africa/Cairo",
  "Africa/Casablanca",
  "Africa/Ceuta",
  "Africa/Conakry",
  "Africa/Dakar",
  "Africa/Dar_es_Salaam",
  "Africa/Djibouti",
  "Africa/Douala",
  "Africa/El_Aaiun",
  "Africa/Freetown",
  "Africa/Gaborone",
  "Africa/Harare",
  "Africa/Johannesburg",
  "Africa/Juba",
  "Africa/Kampala",
  "Africa/Khartoum",
  "Africa/Kigali",
  "Africa/Kinshasa",
  "Africa/Lagos",
  "Africa/Libreville",
  "Africa/Lome",
  "Africa/Luanda",
  "Africa/Lubumbashi",
  "Africa/Lusaka",
  "Africa/Malabo",
  "Africa/Maputo",
  "Africa/Maseru",
  "Africa/Mbabane",
  "Africa/Mogadishu",
  "Africa/Monrovia",
  "Africa/Nairobi",
  "Africa/Ndjamena",
  "Africa/Niamey",
  "Africa/Nouakchott",
  "Africa/Ouagadougou",
  "Africa/Porto-Novo",
  "Africa/Sao_Tome",
  "Africa/Tripoli",
  "Africa/Tunis",
  "Africa/Windhoek",
  "America/Adak",
  "America/Anchorage",
  "America/Anguilla",
  "America/Antigua",
  "America/Araguaina",
  "America/Argentina/La_Rioja",
  "America/Argentina/Rio_Gallegos",
  "America/Argentina/Salta",
  "America/Argentina/San_Juan",
  "America/Argentina/San_Luis",
  "America/Argentina/Tucuman",
  "America/Argentina/Ushuaia",
  "America/Aruba",
  "America/Asuncion",
  "America/Bahia",
  "America/Bahia_Banderas",
  "America/Barbados",
  "America/Belem",
  "America/Belize",
  "America/Blanc-Sablon",
  "America/Boa_Vista",
  "America/Bogota",
  "America/Boise",
  "America/Buenos_Aires",
  "America/Cambridge_Bay",
  "America/Campo_Grande",
  "America/Cancun",
  "America/Caracas",
  "America/Catamarca",
  "America/Cayenne",
  "America/Cayman",
  "America/Chicago",
  "America/Chihuahua",
  "America/Ciudad_Juarez",
  "America/Coral_Harbour",
  "America/Cordoba",
  "America/Costa_Rica",
  "America/Creston",
  "America/Cuiaba",
  "America/Curacao",
  "America/Danmarkshavn",
  "America/Dawson",
  "America/Dawson_Creek",
  "America/Denver",
  "America/Detroit",
  "America/Dominica",
  "America/Edmonton",
  "America/Eirunepe",
  "America/El_Salvador",
  "America/Fort_Nelson",
  "America/Fortaleza",
  "America/Glace_Bay",
  "America/Godthab",
  "America/Goose_Bay",
  "America/Grand_Turk",
  "America/Grenada",
  "America/Guadeloupe",
  "America/Guatemala",
  "America/Guayaquil",
  "America/Guyana",
  "America/Halifax",
  "America/Havana",
  "America/Hermosillo",
  "America/Indiana/Knox",
  "America/Indiana/Marengo",
  "America/Indiana/Petersburg",
  "America/Indiana/Tell_City",
  "America/Indiana/Vevay",
  "America/Indiana/Vincennes",
  "America/Indiana/Winamac",
  "America/Indianapolis",
  "America/Inuvik",
  "America/Iqaluit",
  "America/Jamaica",
  "America/Jujuy",
  "America/Juneau",
  "America/Kentucky/Monticello",
  "America/Kralendijk",
  "America/La_Paz",
  "America/Lima",
  "America/Los_Angeles",
  "America/Louisville",
  "America/Lower_Princes",
  "America/Maceio",
  "America/Managua",
  "America/Manaus",
  "America/Marigot",
  "America/Martinique",
  "America/Matamoros",
  "America/Mazatlan",
  "America/Mendoza",
  "America/Menominee",
  "America/Merida",
  "America/Metlakatla",
  "America/Mexico_City",
  "America/Miquelon",
  "America/Moncton",
  "America/Monterrey",
  "America/Montevideo",
  "America/Montserrat",
  "America/Nassau",
  "America/New_York",
  "America/Nome",
  "America/Noronha",
  "America/North_Dakota/Beulah",
  "America/North_Dakota/Center",
  "America/North_Dakota/New_Salem",
  "America/Ojinaga",
  "America/Panama",
  "America/Paramaribo",
  "America/Phoenix",
  "America/Port-au-Prince",
  "America/Port_of_Spain",
  "America/Porto_Velho",
  "America/Puerto_Rico",
  "America/Punta_Arenas",
  "America/Rankin_Inlet",
  "America/Recife",
  "America/Regina",
  "America/Resolute",
  "America/Rio_Branco",
  "America/Santarem",
  "America/Santiago",
  "America/Santo_Domingo",
  "America/Sao_Paulo",
  "America/Scoresbysund",
  "America/Sitka",
  "America/St_Barthelemy",
  "America/St_Johns",
  "America/St_Kitts",
  "America/St_Lucia",
  "America/St_Thomas",
  "America/St_Vincent",
  "America/Swift_Current",
  "America/Tegucigalpa",
  "America/Thule",
  "America/Tijuana",
  "America/Toronto",
  "America/Tortola",
  "America/Vancouver",
  "America/Whitehorse",
  "America/Winnipeg",
  "America/Yakutat",
  "Antarctica/Casey",
  "Antarctica/Davis",
  "Antarctica/DumontDUrville",
  "Antarctica/Macquarie",
  "Antarctica/Mawson",
  "Antarctica/McMurdo",
  "Antarctica/Palmer",
  "Antarctica/Rothera",
  "Antarctica/Syowa",
  "Antarctica/Troll",
  "Antarctica/Vostok",
  "Arctic/Longyearbyen",
  "Asia/Aden",
  "Asia/Almaty",
  "Asia/Amman",
  "Asia/Anadyr",
  "Asia/Aqtau",
  "Asia/Aqtobe",
  "Asia/Ashgabat",
  "Asia/Atyrau",
  "Asia/Baghdad",
  "Asia/Bahrain",
  "Asia/Baku",
  "Asia/Bangkok",
  "Asia/Barnaul",
  "Asia/Beirut",
  "Asia/Bishkek",
  "Asia/Brunei",
  "Asia/Calcutta",
  "Asia/Chita",
  "Asia/Colombo",
  "Asia/Damascus",
  "Asia/Dhaka",
  "Asia/Dili",
  "Asia/Dubai",
  "Asia/Dushanbe",
  "Asia/Famagusta",
  "Asia/Gaza",
  "Asia/Hebron",
  "Asia/Hong_Kong",
  "Asia/Hovd",
  "Asia/Irkutsk",
  "Asia/Jakarta",
  "Asia/Jayapura",
  "Asia/Jerusalem",
  "Asia/Kabul",
  "Asia/Kamchatka",
  "Asia/Karachi",
  "Asia/Katmandu",
  "Asia/Khandyga",
  "Asia/Krasnoyarsk",
  "Asia/Kuala_Lumpur",
  "Asia/Kuching",
  "Asia/Kuwait",
  "Asia/Macau",
  "Asia/Magadan",
  "Asia/Makassar",
  "Asia/Manila",
  "Asia/Muscat",
  "Asia/Nicosia",
  "Asia/Novokuznetsk",
  "Asia/Novosibirsk",
  "Asia/Omsk",
  "Asia/Oral",
  "Asia/Phnom_Penh",
  "Asia/Pontianak",
  "Asia/Pyongyang",
  "Asia/Qatar",
  "Asia/Qostanay",
  "Asia/Qyzylorda",
  "Asia/Rangoon",
  "Asia/Riyadh",
  "Asia/Saigon",
  "Asia/Sakhalin",
  "Asia/Samarkand",
  "Asia/Seoul",
  "Asia/Shanghai",
  "Asia/Singapore",
  "Asia/Srednekolymsk",
  "Asia/Taipei",
  "Asia/Tashkent",
  "Asia/Tbilisi",
  "Asia/Tehran",
  "Asia/Thimphu",
  "Asia/Tokyo",
  "Asia/Tomsk",
  "Asia/Ulaanbaatar",
  "Asia/Urumqi",
  "Asia/Ust-Nera",
  "Asia/Vientiane",
  "Asia/Vladivostok",
  "Asia/Yakutsk",
  "Asia/Yekaterinburg",
  "Asia/Yerevan",
  "Atlantic/Azores",
  "Atlantic/Bermuda",
  "Atlantic/Canary",
  "Atlantic/Cape_Verde",
  "Atlantic/Faeroe",
  "Atlantic/Madeira",
  "Atlantic/Reykjavik",
  "Atlantic/South_Georgia",
  "Atlantic/St_Helena",
  "Atlantic/Stanley",
  "Australia/Adelaide",
  "Australia/Brisbane",
  "Australia/Broken_Hill",
  "Australia/Darwin",
  "Australia/Eucla",
  "Australia/Hobart",
  "Australia/Lindeman",
  "Australia/Lord_Howe",
  "Australia/Melbourne",
  "Australia/Perth",
  "Australia/Sydney",
  "Europe/Amsterdam",
  "Europe/Andorra",
  "Europe/Astrakhan",
  "Europe/Athens",
  "Europe/Belgrade",
  "Europe/Berlin",
  "Europe/Bratislava",
  "Europe/Brussels",
  "Europe/Bucharest",
  "Europe/Budapest",
  "Europe/Busingen",
  "Europe/Chisinau",
  "Europe/Copenhagen",
  "Europe/Dublin",
  "Europe/Gibraltar",
  "Europe/Guernsey",
  "Europe/Helsinki",
  "Europe/Isle_of_Man",
  "Europe/Istanbul",
  "Europe/Jersey",
  "Europe/Kaliningrad",
  "Europe/Kiev",
  "Europe/Kirov",
  "Europe/Lisbon",
  "Europe/Ljubljana",
  "Europe/London",
  "Europe/Luxembourg",
  "Europe/Madrid",
  "Europe/Malta",
  "Europe/Mariehamn",
  "Europe/Minsk",
  "Europe/Monaco",
  "Europe/Moscow",
  "Europe/Oslo",
  "Europe/Paris",
  "Europe/Podgorica",
  "Europe/Prague",
  "Europe/Riga",
  "Europe/Rome",
  "Europe/Samara",
  "Europe/San_Marino",
  "Europe/Sarajevo",
  "Europe/Saratov",
  "Europe/Simferopol",
  "Europe/Skopje",
  "Europe/Sofia",
  "Europe/Stockholm",
  "Europe/Tallinn",
  "Europe/Tirane",
  "Europe/Ulyanovsk",
  "Europe/Vaduz",
  "Europe/Vatican",
  "Europe/Vienna",
  "Europe/Vilnius",
  "Europe/Volgograd",
  "Europe/Warsaw",
  "Europe/Zagreb",
  "Europe/Zurich",
  "Indian/Antananarivo",
  "Indian/Chagos",
  "Indian/Christmas",
  "Indian/Cocos",
  "Indian/Comoro",
  "Indian/Kerguelen",
  "Indian/Mahe",
  "Indian/Maldives",
  "Indian/Mauritius",
  "Indian/Mayotte",
  "Indian/Reunion",
  "Pacific/Apia",
  "Pacific/Auckland",
  "Pacific/Bougainville",
  "Pacific/Chatham",
  "Pacific/Easter",
  "Pacific/Efate",
  "Pacific/Enderbury",
  "Pacific/Fakaofo",
  "Pacific/Fiji",
  "Pacific/Funafuti",
  "Pacific/Galapagos",
  "Pacific/Gambier",
  "Pacific/Guadalcanal",
  "Pacific/Guam",
  "Pacific/Honolulu",
  "Pacific/Kiritimati",
  "Pacific/Kosrae",
  "Pacific/Kwajalein",
  "Pacific/Majuro",
  "Pacific/Marquesas",
  "Pacific/Midway",
  "Pacific/Nauru",
  "Pacific/Niue",
  "Pacific/Norfolk",
  "Pacific/Noumea",
  "Pacific/Pago_Pago",
  "Pacific/Palau",
  "Pacific/Pitcairn",
  "Pacific/Ponape",
  "Pacific/Port_Moresby",
  "Pacific/Rarotonga",
  "Pacific/Saipan",
  "Pacific/Tahiti",
  "Pacific/Tarawa",
  "Pacific/Tongatapu",
  "Pacific/Truk",
  "Pacific/Wake",
  "Pacific/Wallis"
]

LODGING_TYPES = [
    ('hotel', 'Hotel'),
    ('hostel', 'Hostel'),
    ('resort', 'Resort'),
    ('bnb', 'Bed & Breakfast'),
    ('campground', 'Campground'),
    ('cabin', 'Cabin'),
    ('apartment', 'Apartment'),
    ('house', 'House'),
    ('villa', 'Villa'),
    ('motel', 'Motel'),
    ('other', 'Other')
]

TRANSPORTATION_TYPES = [
    ('car', 'Car'),
    ('plane', 'Plane'),
    ('train', 'Train'),
    ('bus', 'Bus'),
    ('boat', 'Boat'),
    ('bike', 'Bike'),
    ('walking', 'Walking'),
    ('other', 'Other')
]

# Assuming you have a default user ID you want to use
default_user_id = 1  # Replace with an actual user ID

User = get_user_model()

class Visit(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    adventure = models.ForeignKey('Adventure', on_delete=models.CASCADE, related_name='visits')
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    timezone = models.CharField(max_length=50, choices=[(tz, tz) for tz in TIMEZONES], null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.start_date > self.end_date:
            raise ValidationError('The start date must be before or equal to the end date.')

    def __str__(self):
        return f"{self.adventure.name} - {self.start_date} to {self.end_date}"

class Adventure(models.Model):
    #id = models.AutoField(primary_key=True)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user_id)

    category = models.ForeignKey('Category', on_delete=models.SET_NULL, blank=True, null=True)
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True, null=True)
    activity_types = ArrayField(models.CharField(
        max_length=100), blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    rating = models.FloatField(blank=True, null=True)
    link = models.URLField(blank=True, null=True, max_length=2083)
    is_public = models.BooleanField(default=False)

    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    city = models.ForeignKey(City, on_delete=models.SET_NULL, blank=True, null=True)
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, blank=True, null=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, blank=True, null=True)

    # Changed from ForeignKey to ManyToManyField
    collections = models.ManyToManyField('Collection', blank=True, related_name='adventures')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AdventureManager()

    def is_visited_status(self):
        current_date = timezone.now().date()
        for visit in self.visits.all():
            start_date = visit.start_date.date() if isinstance(visit.start_date, timezone.datetime) else visit.start_date
            end_date = visit.end_date.date() if isinstance(visit.end_date, timezone.datetime) else visit.end_date
            if start_date and end_date and (start_date <= current_date):
                return True
            elif start_date and not end_date and (start_date <= current_date):
                return True
        return False

    def clean(self, skip_shared_validation=False):
        """
        Validate model constraints.
        skip_shared_validation: Skip validation when called by shared users
        """
        # Skip validation if this is a shared user update
        if skip_shared_validation:
            return
            
        # Check collections after the instance is saved (in save method or separate validation)
        if self.pk:  # Only check if the instance has been saved
            for collection in self.collections.all():
                if collection.is_public and not self.is_public:
                    raise ValidationError(f'Adventures associated with a public collection must be public. Collection: {collection.name} Adventure: {self.name}')
                
                # Only enforce same-user constraint for non-shared collections
                if self.user_id != collection.user_id:
                    # Check if this is a shared collection scenario
                    # Allow if the adventure owner has access to the collection through sharing
                    if not collection.shared_with.filter(uuid=self.user_id.uuid).exists():
                        raise ValidationError(f'Adventures must be associated with collections owned by the same user or shared collections. Collection owner: {collection.user_id.username} Adventure owner: {self.user_id.username}')
        
        if self.category:
            if self.user_id != self.category.user_id:
                raise ValidationError(f'Adventures must be associated with categories owned by the same user. Category owner: {self.category.user_id.username} Adventure owner: {self.user_id.username}')
            
    def save(self, force_insert=False, force_update=False, using=None, update_fields=None, _skip_geocode=False, _skip_shared_validation=False):
        if force_insert and force_update:
            raise ValueError("Cannot force both insert and updating in model saving.")

        if not self.category:
            category, _ = Category.objects.get_or_create(
                user_id=self.user_id,
                name='general',
                defaults={'display_name': 'General', 'icon': '🌍'}
            )
            self.category = category

        result = super().save(force_insert, force_update, using, update_fields)

        # Validate collections after saving (since M2M relationships require saved instance)
        if self.pk:
            try:
                self.clean(skip_shared_validation=_skip_shared_validation)
            except ValidationError as e:
                # If validation fails, you might want to handle this differently
                # For now, we'll re-raise the error
                raise e

        # ⛔ Skip threading if called from geocode background thread
        if _skip_geocode:
            return result

        if self.latitude and self.longitude:
            thread = threading.Thread(target=background_geocode_and_assign, args=(str(self.id),))
            thread.daemon = True  # Allows the thread to exit when the main program ends
            thread.start()

        return result

    def delete(self, *args, **kwargs):
        # Delete all associated AdventureImages first to trigger their filesystem cleanup
        for image in self.images.all():
            image.delete()
        # Delete all associated Attachment files first to trigger their filesystem cleanup
        for attachment in self.attachments.all():
            attachment.delete()
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.name

class Collection(models.Model):
    #id = models.AutoField(primary_key=True)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user_id)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)
    shared_with = models.ManyToManyField(User, related_name='shared_with', blank=True)
    link = models.URLField(blank=True, null=True, max_length=2083)

    # if connected adventures are private and collection is public, raise an error
    def clean(self):
        if self.is_public and self.pk:  # Only check if the instance has a primary key
            # Updated to use the new related_name 'adventures'
            for adventure in self.adventures.all():
                if not adventure.is_public:
                    raise ValidationError(f'Public collections cannot be associated with private adventures. Collection: {self.name} Adventure: {adventure.name}')

    def __str__(self):
        return self.name
    
class Transportation(models.Model):
    #id = models.AutoField(primary_key=True)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user_id)
    type = models.CharField(max_length=100, choices=TRANSPORTATION_TYPES)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    rating = models.FloatField(blank=True, null=True)
    link = models.URLField(blank=True, null=True)
    date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    start_timezone = models.CharField(max_length=50, choices=[(tz, tz) for tz in TIMEZONES], null=True, blank=True)
    end_timezone = models.CharField(max_length=50, choices=[(tz, tz) for tz in TIMEZONES], null=True, blank=True)
    flight_number = models.CharField(max_length=100, blank=True, null=True)
    from_location = models.CharField(max_length=200, blank=True, null=True)
    origin_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    origin_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    destination_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    destination_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    to_location = models.CharField(max_length=200, blank=True, null=True)
    is_public = models.BooleanField(default=False)
    collection = models.ForeignKey('Collection', on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        print(self.date)
        if self.date and self.end_date and self.date > self.end_date:
            raise ValidationError('The start date must be before the end date. Start date: ' + str(self.date) + ' End date: ' + str(self.end_date))
        
        if self.collection:
            if self.collection.is_public and not self.is_public:
                raise ValidationError('Transportations associated with a public collection must be public. Collection: ' + self.collection.name + ' Transportation: ' + self.name)
            if self.user_id != self.collection.user_id:
                raise ValidationError('Transportations must be associated with collections owned by the same user. Collection owner: ' + self.collection.user_id.username + ' Transportation owner: ' + self.user_id.username)

    def __str__(self):
        return self.name

class Note(models.Model):
    #id = models.AutoField(primary_key=True)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user_id)
    name = models.CharField(max_length=200)
    content = models.TextField(blank=True, null=True)
    links = ArrayField(models.URLField(), blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    is_public = models.BooleanField(default=False)
    collection = models.ForeignKey('Collection', on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.collection:
            if self.collection.is_public and not self.is_public:
                raise ValidationError('Notes associated with a public collection must be public. Collection: ' + self.collection.name + ' Transportation: ' + self.name)
            if self.user_id != self.collection.user_id:
                raise ValidationError('Notes must be associated with collections owned by the same user. Collection owner: ' + self.collection.user_id.username + ' Transportation owner: ' + self.user_id.username)

    def __str__(self):
        return self.name
    
class Checklist(models.Model):
    # id = models.AutoField(primary_key=True)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user_id)
    name = models.CharField(max_length=200)
    date = models.DateField(blank=True, null=True)
    is_public = models.BooleanField(default=False)
    collection = models.ForeignKey('Collection', on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.collection:
            if self.collection.is_public and not self.is_public:
                raise ValidationError('Checklists associated with a public collection must be public. Collection: ' + self.collection.name + ' Checklist: ' + self.name)
            if self.user_id != self.collection.user_id:
                raise ValidationError('Checklists must be associated with collections owned by the same user. Collection owner: ' + self.collection.user_id.username + ' Checklist owner: ' + self.user_id.username)

    def __str__(self):
        return self.name

class ChecklistItem(models.Model):
    #id = models.AutoField(primary_key=True)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user_id)
    name = models.CharField(max_length=200)
    is_checked = models.BooleanField(default=False)
    checklist = models.ForeignKey('Checklist', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.checklist.is_public and not self.checklist.is_public:
            raise ValidationError('Checklist items associated with a public checklist must be public. Checklist: ' + self.checklist.name + ' Checklist item: ' + self.name)
        if self.user_id != self.checklist.user_id:
            raise ValidationError('Checklist items must be associated with checklists owned by the same user. Checklist owner: ' + self.checklist.user_id.username + ' Checklist item owner: ' + self.user_id.username)

    def __str__(self):
        return self.name

@deconstructible
class PathAndRename:
    def __init__(self, path):
        self.path = path

    def __call__(self, instance, filename):
        ext = filename.split('.')[-1]
        # Generate a new UUID for the filename
        filename = f"{uuid.uuid4()}.{ext}"
        return os.path.join(self.path, filename)

class AdventureImage(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, default=default_user_id)
    image = ResizedImageField(
        force_format="WEBP",
        quality=75,
        upload_to=PathAndRename('images/'),
        blank=True,
        null=True,
    )
    immich_id = models.CharField(max_length=200, null=True, blank=True)
    adventure = models.ForeignKey(Adventure, related_name='images', on_delete=models.CASCADE)
    is_primary = models.BooleanField(default=False)

    def clean(self):

        # One of image or immich_id must be set, but not both
        has_image = bool(self.image and str(self.image).strip())
        has_immich_id = bool(self.immich_id and str(self.immich_id).strip())

        if has_image and has_immich_id:
            raise ValidationError("Cannot have both image file and Immich ID. Please provide only one.")
        if not has_image and not has_immich_id:
            raise ValidationError("Must provide either an image file or an Immich ID.")
        
    def save(self, *args, **kwargs):
        # Clean empty strings to None for proper database storage
        if not self.image:
            self.image = None
        if not self.immich_id or not str(self.immich_id).strip():
            self.immich_id = None
            
        self.full_clean()  # This calls clean() method
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Remove file from disk when deleting AdventureImage
        if self.image and os.path.isfile(self.image.path):
            os.remove(self.image.path)
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.image.url if self.image else f"Immich ID: {self.immich_id or 'No image'}"
    
class Attachment(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user_id)
    file = models.FileField(upload_to=PathAndRename('attachments/'),validators=[validate_file_extension])
    adventure = models.ForeignKey(Adventure, related_name='attachments', on_delete=models.CASCADE)
    name = models.CharField(max_length=200, null=True, blank=True)

    def delete(self, *args, **kwargs):
        if self.file and os.path.isfile(self.file.path):
            os.remove(self.file.path)
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.file.url

class Category(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user_id)
    name = models.CharField(max_length=200)
    display_name = models.CharField(max_length=200)
    icon = models.CharField(max_length=200, default='🌍')

    class Meta:
        verbose_name_plural = 'Categories'
        unique_together = ['name', 'user_id']

    def clean(self) -> None:
        self.name = self.name.lower().strip()

        return super().clean()
    
    
    def __str__(self):
        return self.name + ' - ' + self.display_name + ' - ' + self.icon
    
class Lodging(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, default=default_user_id)
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=100, choices=LODGING_TYPES, default='other')
    description = models.TextField(blank=True, null=True)
    rating = models.FloatField(blank=True, null=True)
    link = models.URLField(blank=True, null=True, max_length=2083)
    check_in = models.DateTimeField(blank=True, null=True)
    check_out = models.DateTimeField(blank=True, null=True)
    timezone = models.CharField(max_length=50, choices=[(tz, tz) for tz in TIMEZONES], null=True, blank=True)
    reservation_number = models.CharField(max_length=100, blank=True, null=True)
    price = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    is_public = models.BooleanField(default=False)
    collection = models.ForeignKey('Collection', on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.check_in and self.check_out and self.check_in > self.check_out:
            raise ValidationError('The start date must be before the end date. Start date: ' + str(self.check_in) + ' End date: ' + str(self.check_out))
        
        if self.collection:
            if self.collection.is_public and not self.is_public:
                raise ValidationError('Lodging associated with a public collection must be public. Collection: ' + self.collection.name + ' Loging: ' + self.name)
            if self.user_id != self.collection.user_id:
                raise ValidationError('Lodging must be associated with collections owned by the same user. Collection owner: ' + self.collection.user_id.username + ' Lodging owner: ' + self.user_id.username)

    def __str__(self):
        return self.name