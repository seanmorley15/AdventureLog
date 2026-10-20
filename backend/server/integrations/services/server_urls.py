"""Server URLs for services the user hosts themselves (Endurain, Immich, Wanderer).

The user types the address of their own server, and AdventureLog then calls it. A LAN or
loopback address is fine: that is what a home server is. What must never be reachable through
this field is the machine's own cloud-metadata and link-local addresses, so those are refused,
along with URLs that carry credentials, a query string or a fragment.

Each caller passes ``error``, a function turning a message into the exception it raises, so a
service keeps its own error type and codes.
"""

from urllib.parse import urlparse

from core.net import HostResolutionError, is_blocked_hostname, is_self_hosted_ip, iter_host_ips


def format_server_url(server_url, error):
    """Strip and structurally validate a server URL. No DNS lookups."""
    url = (server_url or '').strip().rstrip('/')
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        raise error('Server URL must be a valid http or https URL.')
    if parsed.username is not None or parsed.password is not None:
        raise error('Server URL must not include username or password.')
    if parsed.query or parsed.fragment:
        raise error('Server URL must not include query parameters or fragments.')
    if not parsed.hostname:
        raise error('Server URL must be a valid http or https URL.')
    path = parsed.path.rstrip('/') if parsed.path else ''
    return f'{parsed.scheme}://{parsed.netloc}{path}'


def assert_host_allowed(hostname, service, error):
    """Refuse a host that is, or resolves to, a metadata or link-local address."""
    if is_blocked_hostname(hostname):
        raise error('Server URL host is not allowed.')

    try:
        for ip in iter_host_ips(hostname):
            if not is_self_hosted_ip(ip):
                raise error('Server URL host is not allowed.')
    except HostResolutionError as exc:
        if exc.kind == HostResolutionError.UNRESOLVABLE:
            raise error(f'Could not resolve {service} server hostname.') from exc
        raise error('Server URL resolved to an invalid IP address.') from exc


def normalize_server_url(server_url, service, error):
    """The cleaned-up base URL of a self-hosted server, or ``error`` if it must not be used."""
    url = format_server_url(server_url, error)
    hostname = urlparse(url).hostname
    if hostname:
        assert_host_allowed(hostname, service, error)
    return url
