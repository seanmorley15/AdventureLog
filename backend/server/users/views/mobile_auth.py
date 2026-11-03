"""Mobile app sign-in through the server's providers. See ``users.services.mobile_auth``."""

from urllib.parse import urlencode, urlparse

from django.contrib.auth import logout
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from users.serializers import MobileTokenRequestSerializer, MobileTokenResponseSerializer
from users.services import mobile_auth
from users.throttling import MobileAuthThrottle


class AppRedirect(HttpResponseRedirect):
    """A redirect back into the app. Only called with a registered redirect URI."""

    def __init__(self, redirect_uri, **params):
        self.allowed_schemes = [urlparse(redirect_uri).scheme]
        params = {k: v for k, v in params.items() if v}
        super().__init__(f'{redirect_uri}?{urlencode(params)}')


@require_GET
@never_cache
def start(request):
    """
    Where the app sends the system browser to sign in with a provider.

    Not part of the JSON API: it answers with redirects. Mistakes that can be reported to the
    app go back to its redirect URI as ``error``; if the redirect URI itself is wrong there is
    nowhere safe to send them, so the browser gets a plain 400.
    """
    params = request.GET
    try:
        login_path = mobile_auth.begin(
            provider=params.get('provider', ''),
            code_challenge=params.get('code_challenge', ''),
            code_challenge_method=params.get('code_challenge_method', ''),
            state=params.get('state', ''),
            redirect_uri=params.get('redirect_uri', ''),
            signed_in=request.user.is_authenticated,
        )
    except mobile_auth.InvalidStart as error:
        redirect_uri = params.get('redirect_uri', '')
        if redirect_uri not in mobile_auth.allowed_redirect_uris():
            return HttpResponseBadRequest(error.message)
        return AppRedirect(
            redirect_uri, error='invalid_request', error_description=error.message, state=params.get('state', '')
        )
    return HttpResponseRedirect(login_path)


@require_GET
@never_cache
def complete(request):
    """Where the browser lands once the provider has signed it in; hands a code to the app."""
    try:
        handoff = mobile_auth.load_handoff(request.GET.get('h', ''))
    except mobile_auth.InvalidHandoff as error:
        return HttpResponseBadRequest(error.message)

    redirect_uri, state = handoff['redirect_uri'], handoff['state']
    if not request.user.is_authenticated:
        return AppRedirect(redirect_uri, error='access_denied', state=state)

    code = mobile_auth.issue_code(
        request.user, challenge=handoff['challenge'], redirect_uri=redirect_uri
    )
    if not handoff['was_signed_in']:
        # The browser session only exists because of this sign-in; do not leave it behind.
        logout(request)
    return AppRedirect(redirect_uri, code=code, state=state)


class MobileTokenView(APIView):
    openapi_tags = ['Authentication']
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [MobileAuthThrottle]

    @extend_schema(request=MobileTokenRequestSerializer, responses=MobileTokenResponseSerializer)
    def post(self, request):
        """
        Exchange a mobile sign-in code for a session token

        The last step of signing in to the mobile app with a provider (OIDC, GitHub...). The
        code arrives in the app's redirect URI; `code_verifier` is the secret whose SHA-256 the
        app sent as `code_challenge`. A code works once and for one minute, and any failed
        attempt spends it. The response matches the other app sign-in responses: send
        `meta.session_token` as `X-Session-Token`.
        """
        data = MobileTokenRequestSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        token = mobile_auth.redeem_code(request._request, **data.validated_data)
        return Response({'status': 200, 'meta': {'is_authenticated': True, 'session_token': token}})
