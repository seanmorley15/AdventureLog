#!/usr/bin/env python3
"""Container healthcheck for the AdventureLog backend."""

from http.client import HTTPConnection
from sys import exit


HOST = "localhost"
PORT = 8000
PATH = "/healthz/"
TIMEOUT_SECONDS = 5


def main() -> int:
    connection = HTTPConnection(HOST, PORT, timeout=TIMEOUT_SECONDS)
    try:
        connection.request("GET", PATH)
        response = connection.getresponse()
        return 0 if 200 <= response.status < 400 else 1
    except Exception:
        return 1
    finally:
        connection.close()


if __name__ == "__main__":
    exit(main())
