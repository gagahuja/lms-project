
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from core.models import Handout
from core.views import (
    HANDOUT_MAX_FILE_SIZE,
    _handout_upload_error,
)


class HandoutUploadValidationTests(SimpleTestCase):
    """Test resource upload validation without modifying the database."""

    def test_accepts_supported_file_extensions(self):
        extensions = (".pdf", ".doc", ".docx", ".ppt", ".pptx")

        for extension in extensions:
            with self.subTest(extension=extension):
                uploaded_file = SimpleUploadedFile(
                    f"sample{extension}",
                    b"test document content",
                )
                self.assertIsNone(
                    _handout_upload_error(uploaded_file)
                )

    def test_accepts_uppercase_extension(self):
        uploaded_file = SimpleUploadedFile(
            "sample.PDF",
            b"test document content",
        )

        self.assertIsNone(_handout_upload_error(uploaded_file))

    def test_rejects_unsupported_file_extensions(self):
        extensions = (".zip", ".exe", ".txt")

        for extension in extensions:
            with self.subTest(extension=extension):
                uploaded_file = SimpleUploadedFile(
                    f"sample{extension}",
                    b"test content",
                )
                self.assertIsNotNone(
                    _handout_upload_error(uploaded_file)
                )

    def test_rejects_missing_file(self):
        self.assertIsNotNone(_handout_upload_error(None))

    def test_rejects_file_larger_than_20_mb(self):
        uploaded_file = SimpleUploadedFile(
            "large.pdf",
            b"x" * (HANDOUT_MAX_FILE_SIZE + 1),
        )

        self.assertIsNotNone(_handout_upload_error(uploaded_file))

    def test_handout_category_choices_and_default(self):
        expected_categories = {
            "study_material": "Study Material",
            "practice_test": "Practice Test",
            "question_paper": "Question Paper",
            "worksheet": "Worksheet",
        }

        self.assertEqual(dict(Handout.CATEGORY_CHOICES), expected_categories)
        self.assertEqual(
            Handout._meta.get_field("category").default,
            "study_material",
        )
