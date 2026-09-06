from __future__ import annotations

import json
from dataclasses import dataclass

from django.contrib.auth import get_user_model
from invitations.adapters import get_invitations_adapter
from invitations.utils import get_invitation_model

User = get_user_model()
Invitation = get_invitation_model()


@dataclass(frozen=True)
class InviteSignupStatus:
    valid: bool
    email: str | None = None
    expired: bool = False
    accepted: bool = False
    registered: bool = False
    message: str | None = None


def normalize_invite_key(key: str | None) -> str | None:
    if not key:
        return None
    normalized = key.strip().lower()
    return normalized or None


def get_invitation_by_key(key: str | None):
    normalized = normalize_invite_key(key)
    if not normalized:
        return None
    try:
        return Invitation.objects.get(key=normalized)
    except Invitation.DoesNotExist:
        return None


def invitation_is_expired(invitation) -> bool:
    """Return True when an invite key is no longer valid."""
    if invitation.sent is None:
        # Admin-created invites may not have a sent timestamp yet.
        return False
    return invitation.key_expired()


def inspect_invite_key(key: str | None) -> InviteSignupStatus:
    invitation = get_invitation_by_key(key)
    if not invitation:
        return InviteSignupStatus(valid=False, message='invalid')

    if invitation.accepted:
        return InviteSignupStatus(
            valid=False,
            email=invitation.email,
            accepted=True,
            message='already_accepted',
        )

    if invitation_is_expired(invitation):
        return InviteSignupStatus(
            valid=False,
            email=invitation.email,
            expired=True,
            message='expired',
        )

    if User.objects.filter(email__iexact=invitation.email).exists():
        return InviteSignupStatus(
            valid=False,
            email=invitation.email,
            registered=True,
            message='already_registered',
        )

    return InviteSignupStatus(valid=True, email=invitation.email)


def stash_invite_email(request, email: str) -> None:
    get_invitations_adapter().stash_verified_email(request, email)


def invite_key_from_request(request) -> str | None:
    key = normalize_invite_key(request.GET.get('invite_key') or request.GET.get('key'))
    if key:
        return key

    if request.method != 'POST':
        return None

    content_type = request.content_type or ''
    if 'application/json' not in content_type:
        return None

    try:
        body = json.loads(request.body.decode() or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    return normalize_invite_key(body.get('invite_key'))


def request_has_valid_invite(request) -> bool:
    if request.session.get('account_verified_email'):
        return True

    status = inspect_invite_key(invite_key_from_request(request))
    return status.valid


def invite_email_for_request(request) -> str | None:
    stashed = request.session.get('account_verified_email')
    if stashed:
        return stashed

    status = inspect_invite_key(invite_key_from_request(request))
    if status.valid:
        return status.email
    return None
