# wanderer_services.py
import requests
from datetime import datetime
from datetime import timezone as dt_timezone
from django.utils import timezone as django_timezone
import logging

from .models import WandererIntegration

logger = logging.getLogger(__name__)

class IntegrationError(Exception):
    pass

# Use both possible cookie names
COOKIE_NAMES = ("pb_auth", "pb-auth")
LOGIN_PATH = "/api/v1/auth/login"

def login_to_wanderer(integration: WandererIntegration, password: str):
    """
    Authenticate with Wanderer and return the auth cookie and expiry.
    """
    url = integration.server_url.rstrip("/") + LOGIN_PATH
    
    try:
        resp = requests.post(url, json={
            "username": integration.username,
            "password": password
        }, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Error connecting to Wanderer login: %s", exc)
        raise IntegrationError("Could not connect to Wanderer server.")

    # Log only summary (not full token body)
    logger.debug("Wanderer login status: %s, headers: %s", resp.status_code, resp.headers.get("Set-Cookie"))

    # Extract auth cookie and expiry
    token = None
    expiry = None
    for cookie in resp.cookies:
        if cookie.name in COOKIE_NAMES:
            token = cookie.value
            if cookie.expires:
                expiry = datetime.fromtimestamp(cookie.expires, tz=dt_timezone.utc)
            else:
                # If no expiry set, assume 24 hours from now
                expiry = django_timezone.now() + django_timezone.timedelta(hours=24)
            break

    if not token:
        logger.error("Wanderer login succeeded but no auth cookie in response.")
        raise IntegrationError("Authentication succeeded, but token cookie not found.")

    logger.info(f"Successfully authenticated with Wanderer. Token expires: {expiry}")
    return token, expiry

def get_valid_session(integration: WandererIntegration, password_for_reauth: str = None):
    """
    Get a requests session with valid authentication.
    Will reuse existing token if valid, or re-authenticate if needed.
    """
    now = django_timezone.now()
    session = requests.Session()
    
    # Check if we have a valid token
    if integration.token and integration.token_expiry and integration.token_expiry > now:
        logger.debug("Using existing valid token")
        session.cookies.set(COOKIE_NAMES[0], integration.token)
        return session

    # Token expired or missing - need to re-authenticate
    if password_for_reauth is None:
        raise IntegrationError("Session expired; password is required to reconnect.")

    logger.info("Token expired, re-authenticating with Wanderer")
    token, expiry = login_to_wanderer(integration, password_for_reauth)
    
    # Update the integration with new token
    integration.token = token
    integration.token_expiry = expiry
    integration.save(update_fields=["token", "token_expiry"])

    # Set the cookie in the session
    session.cookies.set(COOKIE_NAMES[0], token)
    return session

def make_wanderer_request(integration: WandererIntegration, endpoint: str, method: str = "GET", password_for_reauth: str = None, **kwargs):
    """
    Helper function to make authenticated requests to Wanderer API.
    
    Args:
        integration: WandererIntegration instance
        endpoint: API endpoint (e.g., '/api/v1/list')
        method: HTTP method (GET, POST, etc.)
        password_for_reauth: Password to use if re-authentication is needed
        **kwargs: Additional arguments to pass to requests method
    
    Returns:
        requests.Response object
    """
    session = get_valid_session(integration, password_for_reauth)
    url = f"{integration.server_url.rstrip('/')}{endpoint}"
    
    try:
        response = getattr(session, method.lower())(url, timeout=10, **kwargs)
        response.raise_for_status()
        return response
    except requests.RequestException as exc:
        logger.error(f"Error making {method} request to {url}: {exc}")
        raise IntegrationError(f"Error communicating with Wanderer: {exc}")