"""Helpers shared by the serializer modules: how people appear on collections and in comments."""

from core.public_url import build_media_url

def _build_profile_pic_url(user):
    """Return absolute-ish profile pic URL using PUBLIC_URL if available."""
    if not getattr(user, 'profile_pic', None):
        return None

    return build_media_url(user.profile_pic.name)


def _member_roles(collection):

    # Read through the relation so a prefetch of ``members`` is used when present.
    return {member.user_id: member.role for member in collection.members.all()}


def _serialize_collaborator(user, owner_id=None, request_user=None, role=None):
    if not user:
        return None

    return {
        'role': 'owner' if owner_id == user.id else (role or 'editor'),
        'uuid': str(user.uuid),
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'profile_pic': _build_profile_pic_url(user),
        'public_profile': bool(getattr(user, 'public_profile', False)),
        'is_owner': owner_id == user.id,
        'is_current_user': bool(request_user and request_user.id == user.id),
    }
