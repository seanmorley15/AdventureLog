from django.core.management.base import BaseCommand
from adventures.models import Location
import time

class Command(BaseCommand):
	help = 'Bulk geocode all adventures by triggering save on each one'

	def handle(self, *args, **options):
		adventures = Location.objects.all()
		total = adventures.count()
		
		self.stdout.write(self.style.SUCCESS(f'Starting bulk geocoding of {total} adventures'))
		
		for i, adventure in enumerate(adventures):
			try:
				self.stdout.write(f'Processing adventure {i+1}/{total}: {adventure}')
				adventure.save()  # This should trigger any geocoding in the save method
				self.stdout.write(self.style.SUCCESS(f'Successfully processed adventure {i+1}/{total}'))
			except Exception as e:
				self.stdout.write(self.style.ERROR(f'Error processing adventure {i+1}/{total}: {adventure} - {e}'))
			
			# Sleep for 2 seconds between each save
			if i < total - 1:  # Don't sleep after the last one
				time.sleep(2)
		
		self.stdout.write(self.style.SUCCESS('Finished processing all adventures'))
