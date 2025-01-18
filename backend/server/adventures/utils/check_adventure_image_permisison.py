from adventures.models import AdventureImage

def checkAdventureImagePermission(imageId, user):
    """
    Checks if the given user has permission to access the specified adventure image.

    Args:
        imageId (str): The ID of the image to check permissions for.
        user (User): The user object to check permissions against.

    Returns:
        bool: True if the user has permission to access the image, False otherwise.

    Raises:
        AdventureImage.DoesNotExist: If the image with the specified ID does not exist.
    """
    try:
        # Construct the full relative path to match the database field
        image_path = f"images/{imageId}"
        # Fetch the AdventureImage object
        adventure = AdventureImage.objects.get(image=image_path).adventure
        if adventure.is_public:
            return True
        elif adventure.user_id == user:
            return True
        elif adventure.collection:
            if adventure.collection.shared_with.filter(id=user.id).exists():
                return True
        else:
            return False
    except AdventureImage.DoesNotExist:
        print('No image')
        return False
