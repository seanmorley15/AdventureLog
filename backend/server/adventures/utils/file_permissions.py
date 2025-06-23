from adventures.models import AdventureImage, Attachment

protected_paths = ['images/', 'attachments/']

def checkFilePermission(fileId, user, mediaType):
    if mediaType not in protected_paths:
        return True
    if mediaType == 'images/':
        try:
            # Construct the full relative path to match the database field
            image_path = f"images/{fileId}"
            # Fetch the AdventureImage object
            adventure = AdventureImage.objects.get(image=image_path).adventure
            if adventure.is_public:
                return True
            elif adventure.user_id == user:
                return True
            elif adventure.collections.exists():
                # Check if the user is in any collection's shared_with list
                for collection in adventure.collections.all():
                    if collection.shared_with.filter(id=user.id).exists():
                        return True
                return False
            else:
                return False
        except AdventureImage.DoesNotExist:
            return False
    elif mediaType == 'attachments/':
        try:
            # Construct the full relative path to match the database field
            attachment_path = f"attachments/{fileId}"
            # Fetch the Attachment object
            attachment = Attachment.objects.get(file=attachment_path)
            adventure = attachment.adventure
            if adventure.is_public:
                return True
            elif adventure.user_id == user:
                return True
            elif adventure.collections.exists():
                # Check if the user is in any collection's shared_with list
                for collection in adventure.collections.all():
                    if collection.shared_with.filter(id=user.id).exists():
                        return True
                return False
            else:
                return False
        except Attachment.DoesNotExist:
            return False