from django.conf import settings
from django.utils import timezone


def legal_links_required():
    return bool(settings.TERMS_OF_SERVICE_URL or settings.PRIVACY_POLICY_URL)


def build_legal_consent_record():
    return {
        'accepted_at': timezone.now().isoformat(),
        'terms_of_service_url': settings.TERMS_OF_SERVICE_URL or None,
        'privacy_policy_url': settings.PRIVACY_POLICY_URL or None,
    }
