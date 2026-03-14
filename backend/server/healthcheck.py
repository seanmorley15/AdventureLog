#!/usr/bin/env python3
import os
import sys
import urllib.error
import urllib.request


def main() -> int:
    timeout = float(os.getenv('HEALTHCHECK_TIMEOUT_SECONDS', '3'))
    urls = os.getenv(
        'HEALTHCHECK_URLS',
        'http://127.0.0.1:8000/healthz,http://127.0.0.1/healthz',
    )

    for raw_url in urls.split(','):
        url = raw_url.strip()
        if not url:
            continue
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                if response.status == 200:
                    return 0
        except (OSError, urllib.error.URLError):
            continue

    return 1


if __name__ == '__main__':
    sys.exit(main())
