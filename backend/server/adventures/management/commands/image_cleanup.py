import os
from django.core.management.base import BaseCommand
from django.conf import settings
from adventures.models import ContentImage, ContentAttachment
from users.models import CustomUser


class Command(BaseCommand):
	help = 'Find and prompt for deletion of unused image files and attachments in filesystem'

	def add_arguments(self, parser):
		parser.add_argument(
			'--dry-run',
			action='store_true',
			help='Show files that would be deleted without actually deleting them',
		)

	def handle(self, **options):
		dry_run = options['dry_run']
		
		# Get all image and attachment file paths from database
		used_files = set()
		
		# Get ContentImage file paths
		for img in ContentImage.objects.all():
			if img.image and img.image.name:
				used_files.add(os.path.join(settings.MEDIA_ROOT, img.image.name))
		
		# Get Attachment file paths
		for attachment in ContentAttachment.objects.all():
			if attachment.file and attachment.file.name:
				used_files.add(os.path.join(settings.MEDIA_ROOT, attachment.file.name))
		
		# Get user profile picture file paths
		for user in CustomUser.objects.all():
			if user.profile_pic and user.profile_pic.name:
				used_files.add(os.path.join(settings.MEDIA_ROOT, user.profile_pic.name))
		
		# Find all files in media/images and media/attachments directories
		media_root = settings.MEDIA_ROOT
		all_files = []
		
		# Scan images directory
		images_dir = os.path.join(media_root, 'images')
		# Scan attachments directory
		attachments_dir = os.path.join(media_root, 'attachments')
		if os.path.exists(attachments_dir):
			for root, _, files in os.walk(attachments_dir):
				for file in files:
					all_files.append(os.path.join(root, file))
		
		# Scan profile-pics directory
		profile_pics_dir = os.path.join(media_root, 'profile-pics')
		if os.path.exists(profile_pics_dir):
			for root, _, files in os.walk(profile_pics_dir):
				for file in files:
					all_files.append(os.path.join(root, file))
		attachments_dir = os.path.join(media_root, 'attachments')
		if os.path.exists(attachments_dir):
			for root, _, files in os.walk(attachments_dir):
				for file in files:
					all_files.append(os.path.join(root, file))
		
		# Find unused files
		unused_files = [f for f in all_files if f not in used_files]
		
		if not unused_files:
			self.stdout.write(self.style.SUCCESS('No unused files found.'))
			return
		
		self.stdout.write(f'Found {len(unused_files)} unused files:')
		for file_path in unused_files:
			self.stdout.write(f'  {file_path}')
		
		if dry_run:
			self.stdout.write(self.style.WARNING('Dry run mode - no files were deleted.'))
			return
		
		# Prompt for deletion
		confirm = input('\nDo you want to delete these files? (yes/no): ')
		if confirm.lower() in ['yes', 'y']:
			deleted_count = 0
			for file_path in unused_files:
				try:
					os.remove(file_path)
					self.stdout.write(f'Deleted: {file_path}')
					deleted_count += 1
				except OSError as e:
					self.stdout.write(self.style.ERROR(f'Error deleting {file_path}: {e}'))
			
			self.stdout.write(self.style.SUCCESS(f'Successfully deleted {deleted_count} files.'))
		else:
			self.stdout.write('Operation cancelled.')

