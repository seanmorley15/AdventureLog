from adventures.models import LocationImage, Attachment

protected_paths = ['images/', 'attachments/']

def checkFilePermission(fileId, user, mediaType):
    if mediaType not in protected_paths:
        return True
    if mediaType == 'images/':
        try:
            # Construct the full relative path to match the database field
            image_path = f"images/{fileId}"
            # Fetch the AdventureImage object
            location = LocationImage.objects.get(image=image_path).location
            if location.is_public:
                return True
            elif location.user == user:
                return True
            elif location.collections.exists():
                # Check if the user is in any collection's shared_with list
                for collection in location.collections.all():
                    if collection.shared_with.filter(id=user.id).exists():
                        return True
                return False
            else:
                return False
        except LocationImage.DoesNotExist:
            return False
    elif mediaType == 'attachments/':
        try:
            # Construct the full relative path to match the database field
            attachment_path = f"attachments/{fileId}"
            # Fetch the Attachment object
            attachment = Attachment.objects.get(file=attachment_path)
            location = attachment.location
            if location.is_public:
                return True
            elif location.user == user:
                return True
            elif location.collections.exists():
                # Check if the user is in any collection's shared_with list
                for collection in location.collections.all():
                    if collection.shared_with.filter(id=user.id).exists():
                        return True
                return False
            else:
                return False
        except Attachment.DoesNotExist:
            return False