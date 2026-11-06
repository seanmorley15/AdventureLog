"""How an endpoint answers when its work runs in the background."""

from rest_framework import status
from rest_framework.response import Response

from .serializers import BackgroundJobSerializer


def wants_async(request):
    """The client asked for the job to run in the background (``Prefer: respond-async``, RFC 7240)."""
    return 'respond-async' in request.headers.get('Prefer', '').lower()


def accepted(job):
    """``202 Accepted`` with the job and where to poll it."""
    return Response(
        BackgroundJobSerializer(job).data,
        status=status.HTTP_202_ACCEPTED,
        headers={'Location': f'/api/jobs/{job.id}/', 'Preference-Applied': 'respond-async'},
    )
