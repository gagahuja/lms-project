import logging
import mimetypes
from pathlib import Path

import httpx
from asgiref.sync import sync_to_async
from django.http import FileResponse, HttpResponse, StreamingHttpResponse


logger = logging.getLogger(__name__)


def secure_file_response(
    file_field,
    *,
    inline=False,
    content_type=None,
    error_label="File",
):
    """
    Return a file through Django after the calling view has
    completed its authentication and authorization checks.

    The configured Cloudinary storage backend handles retrieval
    through a short-lived signed URL.

    This function never redirects the browser to Cloudinary.
    """

    if not file_field:
        return HttpResponse(
            f"{error_label} not found.",
            status=404,
        )

    file_name = file_field.name or ""
    download_name = Path(file_name).name

    if not download_name:
        return HttpResponse(
            f"{error_label} not found.",
            status=404,
        )

    if not content_type:
        content_type, _ = mimetypes.guess_type(download_name)

    if not content_type:
        content_type = "application/octet-stream"

    try:
        file_handle = file_field.open("rb")

    except FileNotFoundError:
        logger.warning(
            "Protected file not found: category=%s name=%s",
            error_label,
            file_name,
        )
        return HttpResponse(
            f"{error_label} not found.",
            status=404,
        )

    except Exception:
        logger.exception(
            "Protected file retrieval failed: category=%s name=%s",
            error_label,
            file_name,
        )
        return HttpResponse(
            f"Unable to retrieve {error_label.lower()} securely.",
            status=503,
        )

    response = FileResponse(
        file_handle,
        content_type=content_type,
        as_attachment=not inline,
        filename=download_name,
    )

    response["Cache-Control"] = "private, no-store, max-age=0"
    response["Pragma"] = "no-cache"
    response["X-Content-Type-Options"] = "nosniff"
    response["Referrer-Policy"] = "same-origin"

    return response


async def secure_video_stream_response(
    request,
    file_field,
    *,
    error_label="Recording",
    default_content_type="video/mp4",
):
    """
    Stream an authenticated Cloudinary video through Django.

    Preserves HTTP Range requests and responses. Uses an asynchronous
    upstream HTTP client and an asynchronous response iterator so
    ASGI does not buffer the complete video in memory.
    """

    if request.method not in ("GET", "HEAD"):
        response = HttpResponse(
            "Method not allowed.",
            status=405,
        )
        response["Allow"] = "GET, HEAD"
        return response

    if not file_field:
        return HttpResponse(
            f"{error_label} not found.",
            status=404,
        )

    file_name = file_field.name or ""

    if not file_name:
        return HttpResponse(
            f"{error_label} not found.",
            status=404,
        )

    storage = file_field.storage
    signed_url_method = getattr(
        storage,
        "get_signed_download_url",
        None,
    )

    if not callable(signed_url_method):
        logger.error(
            "Protected video storage does not support signed delivery: category=%s",
            error_label,
        )
        return HttpResponse(
            "Unable to retrieve the recording securely.",
            status=503,
        )

    try:
        signed_url = await sync_to_async(
            signed_url_method,
            thread_sensitive=False,
        )(file_name)

    except FileNotFoundError:
        return HttpResponse(
            f"{error_label} not found.",
            status=404,
        )

    except Exception as exc:
        logger.error(
            "Protected video signing failed: category=%s error_type=%s",
            error_label,
            type(exc).__name__,
        )
        return HttpResponse(
            "Unable to retrieve the recording securely.",
            status=503,
        )

    outbound_headers = {
        "Accept-Encoding": "identity",
    }

    # Forward the browser's byte-range request.
    for header_name in ("Range", "If-Range"):
        header_value = request.headers.get(header_name)

        if header_value:
            outbound_headers[header_name] = header_value

    timeout = httpx.Timeout(
        connect=10.0,
        read=60.0,
        write=10.0,
        pool=10.0,
    )

    client = httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        limits=httpx.Limits(
            max_connections=20,
            max_keepalive_connections=10,
        ),
    )

    upstream = None

    try:
        outbound_request = client.build_request(
            request.method,
            signed_url,
            headers=outbound_headers,
        )

        upstream = await client.send(
            outbound_request,
            stream=True,
        )

    except httpx.HTTPError as exc:
        logger.error(
            "Cloudinary video connection failed: category=%s error_type=%s",
            error_label,
            type(exc).__name__,
        )

        if upstream is not None:
            await upstream.aclose()

        await client.aclose()

        return HttpResponse(
            "Unable to retrieve the recording securely.",
            status=503,
        )

    except Exception as exc:
        logger.error(
            "Unexpected protected video error: category=%s error_type=%s",
            error_label,
            type(exc).__name__,
        )

        if upstream is not None:
            await upstream.aclose()

        await client.aclose()

        return HttpResponse(
            "Unable to retrieve the recording securely.",
            status=503,
        )

    # Not-found response from Cloudinary.
    if upstream.status_code == 404:
        await upstream.aclose()
        await client.aclose()

        return HttpResponse(
            f"{error_label} not found.",
            status=404,
        )

    # Supported upstream responses:
    # 200 = complete response
    # 206 = partial byte-range response
    # 416 = requested range is not satisfiable
    if upstream.status_code not in (200, 206, 416):
        upstream_status = upstream.status_code

        await upstream.aclose()
        await client.aclose()

        logger.error(
            "Cloudinary video returned unexpected status: category=%s status=%s",
            error_label,
            upstream_status,
        )

        return HttpResponse(
            "Unable to retrieve the recording securely.",
            status=503,
        )

    async def stream_content():
        try:
            async for chunk in upstream.aiter_raw(
                chunk_size=64 * 1024
            ):
                if chunk:
                    yield chunk

        except httpx.HTTPError as exc:
            logger.error(
                "Protected video stream interrupted: category=%s error_type=%s",
                error_label,
                type(exc).__name__,
            )
            raise

        finally:
            await upstream.aclose()
            await client.aclose()

    content_type = (
        upstream.headers.get("Content-Type")
        or default_content_type
    )

    response = StreamingHttpResponse(
        streaming_content=stream_content(),
        status=upstream.status_code,
        content_type=content_type,
    )

    # Preserve byte-range response metadata.
    for header_name in (
        "Content-Length",
        "Content-Range",
        "ETag",
        "Last-Modified",
    ):
        header_value = upstream.headers.get(header_name)

        if header_value:
            response[header_name] = header_value

    response["Accept-Ranges"] = upstream.headers.get(
        "Accept-Ranges",
        "bytes",
    )

    response["Content-Disposition"] = "inline"
    response["Cache-Control"] = "private, no-store, max-age=0"
    response["Pragma"] = "no-cache"
    response["X-Content-Type-Options"] = "nosniff"
    response["Referrer-Policy"] = "same-origin"
    response["X-Accel-Buffering"] = "no"

    return response
