"""Keeping an account's allauth email record in step with the email set on the account itself."""

from allauth.account.models import EmailAddress


def ensure_email_address(user):
    """
    Give ``user.email`` an allauth ``EmailAddress`` row and make it the primary address.

    Accounts made or edited outside allauth (the Django admin) only set ``user.email``, so
    Settings -> Emails said no email was set while adding that same address failed as a
    duplicate. The row is unverified: signing in through a provider by this email still
    needs the address verified, by the user or by an admin.

    Returns the row, or None when the account has no email.
    """
    email = (user.email or '').strip()
    if not email:
        return None
    address = EmailAddress.objects.filter(user=user, email__iexact=email).first()
    if address is None:
        address = EmailAddress.objects.create(user=user, email=email, primary=False, verified=False)
    if not address.primary:
        address.set_as_primary()
    return address
