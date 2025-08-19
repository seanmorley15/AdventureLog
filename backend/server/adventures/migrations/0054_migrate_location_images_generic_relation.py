# Custom migrations to migrate LocationImage and Attachment models to generic ContentImage and ContentAttachment models
from django.db import migrations, models
from django.utils import timezone

def migrate_images_and_attachments_forward(apps, schema_editor):
    """
    Migrate existing LocationImage and Attachment records to the new generic ContentImage and ContentAttachment models
    """
    # Get the models
    ContentImage = apps.get_model('adventures', 'ContentImage')
    ContentAttachment = apps.get_model('adventures', 'ContentAttachment')

    # Get the ContentType for Location
    ContentType = apps.get_model('contenttypes', 'ContentType')
    try:
        location_ct = ContentType.objects.get(app_label='adventures', model='location')
    except ContentType.DoesNotExist:
        return
    
    # Update existing ContentImages (which were previously LocationImages)
    ContentImage.objects.filter(content_type__isnull=True).update(
        content_type=location_ct
    )
    
    # Set object_id from location_id for ContentImages
    for content_image in ContentImage.objects.filter(object_id__isnull=True):
        if hasattr(content_image, 'location_id') and content_image.location_id:
            content_image.object_id = content_image.location_id
            content_image.save()
    
    # Update existing ContentAttachments (which were previously Attachments)
    ContentAttachment.objects.filter(content_type__isnull=True).update(
        content_type=location_ct
    )
    
    # Set object_id from location_id for ContentAttachments
    for content_attachment in ContentAttachment.objects.filter(object_id__isnull=True):
        if hasattr(content_attachment, 'location_id') and content_attachment.location_id:
            content_attachment.object_id = content_attachment.location_id
            content_attachment.save()
            
def migrate_images_and_attachments_reverse(apps, schema_editor):
    """
    Reverse migration to restore location_id fields from object_id
    """
    ContentImage = apps.get_model('adventures', 'ContentImage')
    ContentAttachment = apps.get_model('adventures', 'ContentAttachment')
    
    # Restore location_id from object_id for ContentImages
    for content_image in ContentImage.objects.all():
        if content_image.object_id and hasattr(content_image, 'location_id'):
            content_image.location_id = content_image.object_id
            content_image.save()
    
    # Restore location_id from object_id for ContentAttachments
    for content_attachment in ContentAttachment.objects.all():
        if content_attachment.object_id and hasattr(content_attachment, 'location_id'):
            content_attachment.location_id = content_attachment.object_id
            content_attachment.save()

class Migration(migrations.Migration):
    
    dependencies = [
        ('adventures', '0053_alter_contentattachment_options_and_more'),
    ]

    operations = [
        migrations.RunPython(
            migrate_images_and_attachments_forward,
            migrate_images_and_attachments_reverse,
            elidable=True
        )
    ]