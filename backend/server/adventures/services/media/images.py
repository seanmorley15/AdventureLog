import ipaddress
import mimetypes
import socket
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse

import requests
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile

from adventures.models import ContentImage
from users.media_utils import enforce_media_storage_limit


def _public_import_error_message(exc):
    """Return a safe, user-facing import error without exposing internal details."""
    if isinstance(exc, ValueError):
        return "Invalid image URL"
    if isinstance(exc, requests.exceptions.Timeout):
        return "Download timeout"
    if isinstance(exc, requests.exceptions.RequestException):
        return "Failed to fetch image from the remote server"
    return "Image import failed"


def _is_safe_url(image_url):
    """
    Validate a URL for safe proxy use.
    Returns (True, parsed) on success or (False, error_message) on failure.
    Checks:
    - Scheme is http or https
    - No non-standard ports (only 80 and 443 allowed)
    - All resolved IPs are public (no private/loopback/reserved/link-local/multicast)
    """
    parsed = urlparse(image_url)

    if parsed.scheme not in ("http", "https"):
        return False, "Invalid URL scheme. Only http and https are allowed."

    port = parsed.port
    if port is not None and port not in (80, 443):
        return False, "Non-standard ports are not allowed."

    hostname = parsed.hostname
    if not hostname:
        return False, "Invalid URL: missing hostname."

    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False, "Could not resolve hostname."

    if not addr_infos:
        return False, "Could not resolve hostname."

    for addr_info in addr_infos:
        try:
            ip = ipaddress.ip_address(addr_info[4][0])
        except ValueError:
            return False, "Invalid IP address resolved from hostname."
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_reserved
            or ip.is_link_local
            or ip.is_multicast
        ):
            return False, "Access to internal networks is not allowed."

    return True, parsed


def download_remote_image(image_url):
    safe, result = _is_safe_url(image_url)
    if not safe:
        raise ValueError(result)

    headers = {"User-Agent": "AdventureLog/1.0 (Image Import)"}
    max_redirects = 3
    current_url = image_url

    response = None
    for _ in range(max_redirects + 1):
        response = requests.get(
            current_url,
            timeout=10,
            headers=headers,
            stream=True,
            allow_redirects=False,
        )

        if not response.is_redirect:
            break

        redirect_url = response.headers.get("Location", "")
        if not redirect_url:
            raise ValueError("Redirect with missing Location header")

        # Handle relative redirects safely.
        redirect_url = urljoin(current_url, redirect_url)

        safe, result = _is_safe_url(redirect_url)
        if not safe:
            raise ValueError(f"Redirect blocked: {result}")

        current_url = redirect_url
    else:
        raise ValueError("Too many redirects")

    if response is None:
        raise ValueError("Failed to fetch image")

    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
    if not content_type.startswith("image/"):
        raise ValueError("URL does not point to an image")

    content_length = response.headers.get("Content-Length")
    if content_length and int(content_length) > 20 * 1024 * 1024:
        raise ValueError("Image too large (max 20MB)")

    ext = mimetypes.guess_extension(content_type) or ".jpg"
    if ext == ".jpe":
        ext = ".jpg"

    return {
        "filename": f"remote_{uuid.uuid4().hex}{ext}",
        "content": response.content,
        "content_type": content_type,
        "source_url": image_url,
    }


def import_remote_images_for_object(content_object, urls, owner=None, max_workers=5):
    """Download remote URLs and attach them as ContentImage records for a content object."""
    content_type = ContentType.objects.get_for_model(content_object.__class__)
    object_id = str(content_object.id)
    image_owner = owner or getattr(content_object, "user", None)

    downloaded_results = []
    worker_count = max(1, min(max_workers, len(urls)))

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {
            executor.submit(download_remote_image, image_url): (index, image_url)
            for index, image_url in enumerate(urls)
        }

        for future in as_completed(futures):
            index, image_url = futures[future]
            try:
                file_data = future.result()
                downloaded_results.append((index, image_url, file_data, None))
            except Exception as exc:
                downloaded_results.append((index, image_url, None, _public_import_error_message(exc)))

    downloaded_results.sort(key=lambda item: item[0])

    existing_image_count = ContentImage.objects.filter(
        content_type=content_type,
        object_id=object_id,
    ).count()
    set_primary_next = existing_image_count == 0

    created_images = []
    results = []
    failed = []

    for _, image_url, file_data, error_message in downloaded_results:
        if error_message:
            failure = {
                "url": image_url,
                "error": error_message,
            }
            results.append({
                **failure,
                "status": "failed",
            })
            failed.append(failure)
            continue

        incoming_bytes = len(file_data["content"])
        allowed, details = enforce_media_storage_limit(image_owner, incoming_bytes)
        if not allowed:
            failure = {
                "url": image_url,
                "error": "Media storage limit exceeded",
                "details": details,
            }
            results.append({
                **failure,
                "status": "failed",
            })
            failed.append(failure)
            continue

        image_file = ContentFile(file_data["content"], name=file_data["filename"])
        image = ContentImage.objects.create(
            user=image_owner,
            image=image_file,
            content_type=content_type,
            object_id=object_id,
            is_primary=set_primary_next,
        )
        if set_primary_next:
            set_primary_next = False

        created_images.append(image)
        results.append({
            "url": image_url,
            "status": "success",
            "image_id": image.id,
        })

    return {
        "created": created_images,
        "created_count": len(created_images),
        "failed": failed,
        "failed_count": len(failed),
        "results": results,
    }
