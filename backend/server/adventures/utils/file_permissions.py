from adventures.models import ContentImage, ContentAttachment

from adventures.models import Visit

protected_paths = ['images/', 'attachments/']

def checkFilePermission(fileId, user, mediaType):
    if mediaType not in protected_paths:
        return True
    if mediaType == 'images/':
        try:
            # Construct the full relative path to match the database field
            image_path = f"images/{fileId}"
            # Fetch the ContentImage object
            content_image = ContentImage.objects.get(image=image_path)
            
            # Get the content object (could be Location, Transportation, Note, etc.)
            content_object = content_image.content_object

            # handle differently when content_object is a Visit, get the location instead
            if isinstance(content_object, Visit):
                # check visit.location
                if content_object.location:
                    # continue with the location check
                    content_object = content_object.location

            # Check if content object is public
            if hasattr(content_object, 'is_public') and content_object.is_public:
                return True
            
            # Check if user owns the content object
            if hasattr(content_object, 'user') and content_object.user == user:
                return True
            
            # Check collection-based permissions
            if hasattr(content_object, 'collections') and content_object.collections.exists():
                # For objects with multiple collections (like Location)
                for collection in content_object.collections.all():
                    if collection.user == user or collection.shared_with.filter(id=user.id).exists():
                        return True
                return False
            elif hasattr(content_object, 'collection') and content_object.collection:
                # For objects with single collection (like Transportation, Note, etc.)
                if content_object.collection.user == user or content_object.collection.shared_with.filter(id=user.id).exists():
                    return True
                return False
            else:
                return False
                
        except ContentImage.DoesNotExist:
            return False
    elif mediaType == 'attachments/':
        try:
            # Construct the full relative path to match the database field
            attachment_path = f"attachments/{fileId}"
            # Fetch the ContentAttachment object
            content_attachment = ContentAttachment.objects.get(file=attachment_path)
            
            # Get the content object (could be Location, Transportation, Note, etc.)
            content_object = content_attachment.content_object
            
            # Check if content object is public
            if hasattr(content_object, 'is_public') and content_object.is_public:
                return True
            
            # Check if user owns the content object
            if hasattr(content_object, 'user') and content_object.user == user:
                return True
            
            # Check collection-based permissions
            if hasattr(content_object, 'collections') and content_object.collections.exists():
                # For objects with multiple collections (like Location)
                for collection in content_object.collections.all():
                    if collection.user == user or collection.shared_with.filter(id=user.id).exists():
                        return True
                return False
            elif hasattr(content_object, 'collection') and content_object.collection:
                # For objects with single collection (like Transportation, Note, etc.)
                if content_object.collection.user == user or content_object.collection.shared_with.filter(id=user.id).exists():
                    return True
                return False
            else:
                return False
                
        except ContentAttachment.DoesNotExist:
            return False