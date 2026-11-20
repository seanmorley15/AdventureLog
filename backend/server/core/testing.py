"""Small helpers shared by the tests of every app."""

from django.contrib.auth import get_user_model


def make_user(name, **extra):
    """A user named ``name`` with a matching e-mail address and a known password."""
    extra.setdefault('password', 'testpassword123')
    return get_user_model().objects.create_user(username=name, email=f'{name}@example.com', **extra)
