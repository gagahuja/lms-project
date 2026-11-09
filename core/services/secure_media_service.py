import logging
import mimetypes
from pathlib import Path

from django.http import FileResponse, HttpResponse


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
