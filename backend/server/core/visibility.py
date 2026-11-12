"""
Who may see what is published, and whose profile.

Three audiences, narrowest first: private (the owner and the people they share with), signed-in
users of this server, and anyone. ``ALLOW_PUBLIC_ACCESS=False`` removes the last one: what is
public is then shown to signed-in users only (#1124).

Profiles (#1226) use the same ladder in ``profile_visibility``. A profile shown to signed-in users
or to anyone can be found and invited to share a collection; a private one cannot.

Every app checks profiles and published things through these helpers, so the server-wide switch
applies the same way everywhere.
"""
from django.conf import settings
from django.db import models
from django.db.models import Q


class ProfileVisibility(models.TextChoices):
    PRIVATE = 'private', 'Private'
    SIGNED_IN = 'signed_in', 'Signed-in users'
    PUBLIC = 'public', 'Public'


def public_access_allowed() -> bool:
    """Whether people who are not signed in may see anything on this server."""
    return bool(getattr(settings, 'ALLOW_PUBLIC_ACCESS', True))


def is_signed_in(user) -> bool:
    return bool(user is not None and getattr(user, 'is_authenticated', False))


def can_read_published(user) -> bool:
    """Whether ``user`` may see what is published to the public: anyone, or only signed-in users."""
    return public_access_allowed() or is_signed_in(user)


def _levels_seen_by(viewer):
    if is_signed_in(viewer):
        return [ProfileVisibility.SIGNED_IN, ProfileVisibility.PUBLIC]
    if public_access_allowed():
        return [ProfileVisibility.PUBLIC]
    return []


def can_see_profile_level(viewer, level) -> bool:
    """Whether ``viewer`` may see a profile whose visibility is ``level`` (not counting their own)."""
    return level in _levels_seen_by(viewer)


def can_see_profile(viewer, user) -> bool:
    """Whether ``viewer`` (a user, or None / anonymous) may see ``user``'s profile."""
    if is_signed_in(viewer) and viewer.pk == user.pk:
        return True
    return can_see_profile_level(viewer, user.profile_visibility)


def visible_profiles_q(viewer, prefix='') -> Q:
    """Q matching the users whose profile ``viewer`` may see. ``prefix`` is the path to the user."""
    q = Q(**{f'{prefix}profile_visibility__in': _levels_seen_by(viewer)})
    if is_signed_in(viewer):
        q |= Q(**{f'{prefix}pk': viewer.pk})
    return q


SHAREABLE_LEVELS = (ProfileVisibility.SIGNED_IN, ProfileVisibility.PUBLIC)


def is_shareable(user) -> bool:
    """Whether others may find ``user`` and invite them to a collection."""
    return user.profile_visibility in SHAREABLE_LEVELS


def shareable_profiles_q(prefix='') -> Q:
    return Q(**{f'{prefix}profile_visibility__in': SHAREABLE_LEVELS})
