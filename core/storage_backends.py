import logging
import os
import time
from pathlib import Path

import cloudinary.api
import cloudinary.exceptions
import cloudinary.uploader
import cloudinary.utils
import requests

from django.core.files.base import ContentFile
from django.utils.deconstruct import deconstructible

from cloudinary_storage.storage import (
    RawMediaCloudinaryStorage,
    VideoMediaCloudinaryStorage,
)


logger = logging.getLogger(__name__)


@deconstructible
class AuthenticatedCloudinaryStorageMixin:
    """
    Cloudinary storage mixin for authenticated media.

    New uploads use Cloudinary's authenticated delivery type.

    During migration, existing assets uploaded with the ordinary
    'upload' delivery type remain readable and deletable.

    Browser-facing public URLs are deliberately disabled.
    Protected Django views should use get_signed_download_url().
    """

    AUTHENTICATED_TYPE = "authenticated"
    LEGACY_TYPE = "upload"

    REQUEST_TIMEOUT = (5, 60)
    DEFAULT_URL_EXPIRY = 120

    def _get_public_id(self, name):
        name = self._normalise_name(name)
        return self._prepend_prefix(name)

    def get_asset_details(self, name):
        """
        Retrieve asset metadata, checking authenticated assets first
        and legacy public-upload assets second.

        Returns:
            (asset_details, actual_cloudinary_delivery_type)

        Only a genuine Cloudinary NotFound response triggers fallback.
        Authentication, permission, rate-limit and network errors
        are allowed to propagate.
        """

        public_id = self._get_public_id(name)
        resource_type = self._get_resource_type(name)

        for delivery_type in (
            self.AUTHENTICATED_TYPE,
            self.LEGACY_TYPE,
        ):
            try:
                details = cloudinary.api.resource(
                    public_id,
                    resource_type=resource_type,
                    type=delivery_type,
                )

                return details, delivery_type

            except cloudinary.exceptions.NotFound:
                continue

        raise FileNotFoundError(
            "Cloudinary asset was not found."
        )

    def get_signed_download_url(
        self,
        name,
        expires_in=None,
    ):
        """
        Generate a short-lived signed Cloudinary download URL.

        The actual asset delivery type is determined from Cloudinary
        metadata so legacy uploads remain readable during migration.
        """

        details, delivery_type = self.get_asset_details(name)

        file_format = (
            details.get("format")
            or Path(name).suffix.lstrip(".")
        )

        if not file_format:
            raise IOError(
                "Cloudinary asset format could not be determined."
            )

        expiry = (
            expires_in
            if expires_in is not None
            else self.DEFAULT_URL_EXPIRY
        )

        if not isinstance(expiry, int) or expiry <= 0:
            raise ValueError(
                "Download URL expiry must be a positive integer."
            )

        return cloudinary.utils.private_download_url(
            self._get_public_id(name),
            file_format.lower(),
            resource_type=self._get_resource_type(name),
            type=delivery_type,
            expires_at=int(time.time()) + expiry,
        )

    def _upload(self, name, content):
        """
        Upload a new asset using authenticated delivery.
        """

        options = {
            "use_filename": True,
            "resource_type": self._get_resource_type(name),
            "tags": self.TAG,
            "type": self.AUTHENTICATED_TYPE,
        }

        folder = os.path.dirname(name)

        if folder:
            options["folder"] = folder

        return cloudinary.uploader.upload(
            content,
            **options,
        )

    def _open(self, name, mode="rb"):
        """
        Open an asset through a short-lived signed download URL.

        This method supports both new authenticated assets and
        legacy upload assets during the migration period.
        """

        signed_url = self.get_signed_download_url(name)

        try:
            with requests.get(
                signed_url,
                timeout=self.REQUEST_TIMEOUT,
            ) as response:

                if response.status_code == 404:
                    raise FileNotFoundError(
                        "Cloudinary asset was not found."
                    )

                response.raise_for_status()
                file_content = response.content

        except requests.RequestException:
            logger.exception(
                "Secure Cloudinary file retrieval failed."
            )
            raise

        file = ContentFile(file_content)
        file.name = name
        file.mode = mode

        return file

    def url(self, name):
        """
        Do not expose permanent Cloudinary delivery URLs.

        Browser delivery must go through an authenticated Django view.
        """

        return ""

    def delete(self, name):
        """
        Delete an asset using its actual Cloudinary delivery type.
        """

        try:
            _, delivery_type = self.get_asset_details(name)

        except FileNotFoundError:
            return False

        response = cloudinary.uploader.destroy(
            self._get_public_id(name),
            invalidate=True,
            resource_type=self._get_resource_type(name),
            type=delivery_type,
        )

        return response.get("result") == "ok"

    def exists(self, name):
        """
        Check Cloudinary metadata without requesting a public URL.
        """

        try:
            self.get_asset_details(name)
            return True

        except FileNotFoundError:
            return False

    def size(self, name):
        """
        Return the asset size from Cloudinary metadata.
        """

        try:
            details, _ = self.get_asset_details(name)

        except FileNotFoundError:
            return None

        file_size = details.get("bytes")

        return int(file_size) if file_size is not None else None


@deconstructible
class AuthenticatedRawMediaCloudinaryStorage(
    AuthenticatedCloudinaryStorageMixin,
    RawMediaCloudinaryStorage,
):
    """
    Authenticated Cloudinary storage for RAW resources.
    """
    pass


@deconstructible
class AuthenticatedVideoMediaCloudinaryStorage(
    AuthenticatedCloudinaryStorageMixin,
    VideoMediaCloudinaryStorage,
):
    """
    Authenticated Cloudinary storage for VIDEO resources.
    """
    pass
