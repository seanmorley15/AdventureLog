# myapp/management/commands/seed.py

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from adventures.models import Location


class Command(BaseCommand):
    help = 'Imports the featured adventures'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        username = input(
            "Enter a username to own the featured adventures: ")

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                f'User with username "{username}" does not exist.'))
            return

        adventures = [
            ('Yellowstone National Park', 'Wyoming, Montana, Idaho, USA', 'featured'),
            ('Yosemite National Park', 'California, USA', 'featured'),
            ('Banff National Park', 'Alberta, Canada', 'featured'),
            ('Kruger National Park', 'Limpopo, South Africa', 'featured'),
            ('Grand Canyon National Park', 'Arizona, USA', 'featured'),
            ('Great Smoky Mountains National Park',
             'North Carolina, Tennessee, USA', 'featured'),
            ('Zion National Park', 'Utah, USA', 'featured'),
            ('Glacier National Park', 'Montana, USA', 'featured'),
            ('Rocky Mountain National Park', 'Colorado, USA', 'featured'),
            ('Everglades National Park', 'Florida, USA', 'featured'),
            ('Arches National Park', 'Utah, USA', 'featured'),
            ('Acadia National Park', 'Maine, USA', 'featured'),
            ('Sequoia National Park', 'California, USA', 'featured'),
        ]

        for name, location, type_ in adventures:
            Location.objects.create(
                user=user,
                name=name,
                location=location,
                type=type_,
                is_public=True
            )

        self.stdout.write(self.style.SUCCESS(
            'Successfully inserted featured adventures!'))
