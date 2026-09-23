import logging
import shutil
import subprocess
import tempfile
from pathlib import Path


logger = logging.getLogger(__name__)


OFFICE_PREVIEW_EXTENSIONS = {
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
}


class DocumentPreviewError(Exception):
    """Raised when an Office document cannot be converted to PDF."""


def is_office_preview_file(file_name):
    """
    Return True when the file is an Office document
    that ScoreSkill can convert to a PDF preview.
    """

    extension = Path(
        file_name or ""
    ).suffix.lower()

    return extension in OFFICE_PREVIEW_EXTENSIONS


def _find_soffice():
    """
    Locate the LibreOffice command-line executable.

    Supports:
    - PATH based installation
    - standard Windows installation
    - common Linux installation paths
    """

    candidates = [
        shutil.which("soffice"),
        shutil.which("libreoffice"),
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "/usr/bin/soffice",
        "/usr/local/bin/soffice",
    ]

    for candidate in candidates:

        if not candidate:
            continue

        if Path(candidate).exists():
            return candidate

    return None


def convert_cloudinary_file_to_pdf(file_field):
    """
    Convert a stored Office document to PDF and return
    the generated PDF as bytes.

    The source document is never exposed to the browser.
    """

    file_name = file_field.name or ""

    if not is_office_preview_file(file_name):

        raise DocumentPreviewError(
            "This file type does not support document preview."
        )

    soffice = _find_soffice()

    if not soffice:

        raise DocumentPreviewError(
            "LibreOffice is not available on this server."
        )

    extension = Path(
        file_name
    ).suffix.lower()

    try:

        with tempfile.TemporaryDirectory(
            prefix="scoreskill-office-"
        ) as temp_dir:

            temp_path = Path(temp_dir)

            source_path = (
                temp_path / f"input{extension}"
            )

            output_path = (
                temp_path / "input.pdf"
            )

            profile_path = (
                temp_path / "lo_profile"
            )

            # -------------------------------------------------
            # DOWNLOAD SOURCE FILE TO TEMPORARY STORAGE
            # -------------------------------------------------

            with file_field.open("rb") as source:

                with source_path.open("wb") as destination:

                    shutil.copyfileobj(
                        source,
                        destination,
                    )

            # -------------------------------------------------
            # CONVERT OFFICE FILE -> PDF
            # -------------------------------------------------

            command = [
                soffice,
                "--headless",
                f"-env:UserInstallation={profile_path.as_uri()}",
                "--convert-to",
                "pdf",
                "--outdir",
                str(temp_path),
                str(source_path),
            ]

            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60,
                check=False,
            )

            if result.returncode != 0:

                logger.error(
                    "LibreOffice conversion failed. "
                    "returncode=%s stdout=%s stderr=%s",
                    result.returncode,
                    result.stdout,
                    result.stderr,
                )

                raise DocumentPreviewError(
                    "Unable to convert the document to PDF."
                )

            if not output_path.exists():

                logger.error(
                    "LibreOffice returned success but "
                    "no PDF was created. stdout=%s stderr=%s",
                    result.stdout,
                    result.stderr,
                )

                raise DocumentPreviewError(
                    "PDF preview was not created."
                )

            return output_path.read_bytes()

    except subprocess.TimeoutExpired as exc:

        logger.error(
            "LibreOffice conversion timed out: %s",
            exc,
        )

        raise DocumentPreviewError(
            "Document conversion timed out."
        ) from exc

    except OSError as exc:

        logger.exception(
            "Unable to execute LibreOffice."
        )

        raise DocumentPreviewError(
            "Unable to process the document."
        ) from exc