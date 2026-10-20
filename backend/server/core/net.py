"""DNS helpers for code that makes outbound requests.

Only name resolution is shared. Which addresses are acceptable is a policy decision
that differs per feature, so each caller applies its own:

* ``check_public_http_url`` and ``public_session`` - user-supplied URLs fetched server-side
  (public internet only). The first rejects a URL up front; the second enforces the same rule
  at connect time, on the address actually used, so a name that resolves differently the second
  time (DNS rebinding) cannot reach an internal host.
* ``integrations.services.endurain`` - self-hosted servers, so LAN addresses are allowed.
"""

import ipaddress
import socket
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool
from urllib3.exceptions import NewConnectionError
from urllib3.util.connection import create_connection


class HostResolutionError(Exception):
    UNRESOLVABLE = 'unresolvable'
    INVALID_ADDRESS = 'invalid_address'

    def __init__(self, kind):
        super().__init__(kind)
        self.kind = kind


def iter_host_ips(hostname):
    """
    Yield each address a hostname resolves to, one at a time.

    Raises HostResolutionError when the name does not resolve, or when the resolver
    returns something that is not an IP address. The errors surface during iteration, so
    a caller that rejects an earlier address never sees a later malformed one.
    """
    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise HostResolutionError(HostResolutionError.UNRESOLVABLE) from exc

    if not addr_infos:
        raise HostResolutionError(HostResolutionError.UNRESOLVABLE)

    for addr_info in addr_infos:
        try:
            yield ipaddress.ip_address(addr_info[4][0])
        except ValueError as exc:
            raise HostResolutionError(HostResolutionError.INVALID_ADDRESS) from exc


def is_resolvable(hostname):
    """Whether DNS can currently resolve the hostname. A reachability probe, not a security check."""
    try:
        socket.gethostbyname(hostname)
        return True
    except socket.error:
        return False


def is_public_ip(ip):
    """
    Whether an address is on the public internet.

    ``is_global`` also rules out carrier-grade NAT (100.64.0.0/10) and the documentation and
    benchmarking ranges, which the private/loopback/reserved checks alone let through. An IPv4
    address written as IPv6 (``::ffff:127.0.0.1``) is judged as the IPv4 address it is.
    """
    if ip.version == 6 and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast and not ip.is_reserved


def check_public_http_url(url):
    """
    Decide whether the server may fetch a user-supplied URL.

    Returns ``(True, parsed_url)`` or ``(False, reason)``. Only http(s) on ports 80/443 to
    hosts whose every address is on the public internet is accepted. Callers must call it
    again for each redirect target.
    """
    parsed = urlparse(url)

    if parsed.scheme not in ('http', 'https'):
        return False, 'Invalid URL scheme. Only http and https are allowed.'

    port = parsed.port
    if port is not None and port not in (80, 443):
        return False, 'Non-standard ports are not allowed.'

    hostname = parsed.hostname
    if not hostname:
        return False, 'Invalid URL: missing hostname.'

    try:
        for ip in iter_host_ips(hostname):
            if not is_public_ip(ip):
                return False, 'Access to internal networks is not allowed.'
    except HostResolutionError as exc:
        if exc.kind == HostResolutionError.UNRESOLVABLE:
            return False, 'Could not resolve hostname.'
        return False, 'Invalid IP address resolved from hostname.'

    return True, parsed


METADATA_NETWORKS = (
    ipaddress.ip_network('169.254.0.0/16'),  # link-local / cloud metadata
    ipaddress.ip_network('fd00:ec2::/32'),  # AWS IPv6 metadata
)
BLOCKED_HOSTNAMES = frozenset({
    'metadata.google.internal',
    'metadata.google.com',
    'instance-data',
})


def is_self_hosted_ip(ip):
    """
    Whether a server the user runs themselves may live at this address.

    A home server is on a LAN or loopback, so private addresses are fine. Cloud-metadata and
    link-local addresses (where instance credentials live), multicast, and the unspecified
    address never are.
    """
    if ip.version == 6 and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    if ip.is_multicast or ip.is_unspecified or ip.is_link_local:
        return False
    return not any(ip in network for network in METADATA_NETWORKS)


def is_blocked_hostname(hostname):
    hostname = hostname.lower().rstrip('.')
    return hostname in BLOCKED_HOSTNAMES or hostname.endswith('.metadata.google.internal')


def _connect_checked(allowed):
    """A replacement for ``HTTPConnection._new_conn``: resolve once, check every address, dial a checked one."""

    def new_conn(self):
        if is_blocked_hostname(self._dns_host):
            raise NewConnectionError(self, f'{self._dns_host} is not an allowed host')
        try:
            infos = socket.getaddrinfo(self._dns_host, self.port, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise NewConnectionError(self, f'Could not resolve {self._dns_host}: {exc}') from exc

        addresses = [info[4][0] for info in infos]
        for address in addresses:
            try:
                ok = allowed(ipaddress.ip_address(address))
            except ValueError:
                ok = False
            if not ok:
                raise NewConnectionError(self, f'{self._dns_host} resolves to a disallowed address')

        last_error = None
        for address in addresses:
            try:
                return create_connection(
                    (address, self.port),
                    self.timeout,
                    source_address=self.source_address,
                    socket_options=self.socket_options,
                )
            except OSError as exc:
                last_error = exc
        raise NewConnectionError(self, f'Could not connect to {self._dns_host}: {last_error}') from last_error

    return new_conn


def _adapter_class(name, allowed):
    new_conn = _connect_checked(allowed)

    # TLS is still verified against the host name; only the address that is dialled is pinned.
    http_connection = type(f'{name}HTTPConnection', (HTTPConnection,), {'_new_conn': new_conn})
    https_connection = type(f'{name}HTTPSConnection', (HTTPSConnection,), {'_new_conn': new_conn})
    http_pool = type(f'{name}HTTPPool', (HTTPConnectionPool,), {'ConnectionCls': http_connection})
    https_pool = type(f'{name}HTTPSPool', (HTTPSConnectionPool,), {'ConnectionCls': https_connection})

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        HTTPAdapter.init_poolmanager(self, connections, maxsize, block=block, **pool_kwargs)
        self.poolmanager.pool_classes_by_scheme = {'http': http_pool, 'https': https_pool}

    return type(f'{name}Adapter', (HTTPAdapter,), {'init_poolmanager': init_poolmanager})


PublicOnlyAdapter = _adapter_class('PublicOnly', is_public_ip)
SelfHostedAdapter = _adapter_class('SelfHosted', is_self_hosted_ip)


def _session(adapter_class):
    session = requests.Session()
    adapter = adapter_class()
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def public_session():
    """
    A requests session for fetching a user-supplied URL.

    Connections are refused unless every address the host name resolves to is public. A
    configured outbound proxy resolves names itself, so requests that use one are not covered.
    """
    return _session(PublicOnlyAdapter)


def self_hosted_session():
    """
    A requests session for talking to a server the user runs themselves (Immich, Wanderer).

    LAN and loopback addresses are allowed; cloud-metadata and link-local ones are not. The
    check is made on the address actually dialled.
    """
    return _session(SelfHostedAdapter)
