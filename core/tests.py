from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, SimpleTestCase

from core.models import Handout
from core.views import (
    HANDOUT_MAX_FILE_SIZE,
    _handout_upload_error,
    add_teacher_lesson_handout,
    edit_teacher_lesson_handout,
    delete_teacher_lesson_handout,
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


class LessonHandoutWorkflowTests(SimpleTestCase):
    """Test lesson Handout views without using the database."""

    def setUp(self):
        self.factory = RequestFactory()

        self.teacher = SimpleNamespace(
            is_authenticated=True,
            user_type="teacher",
            id=7,
        )
        self.other_teacher = SimpleNamespace(
            is_authenticated=True,
            user_type="teacher",
            id=8,
        )

        self.course = SimpleNamespace(
            id=42,
            teacher_id=self.teacher.id,
        )
        self.module = SimpleNamespace(
            id=5,
            course=self.course,
        )
        self.lesson = SimpleNamespace(
            id=9,
            module=self.module,
        )

    def make_request(self, user, data):
        request = self.factory.post("/test/", data=data)
        request.user = user
        return request

    def test_teacher_can_create_lesson_handout(self):
        uploaded_file = SimpleUploadedFile(
            "worksheet.pdf",
            b"test PDF content",
        )
        request = self.make_request(
            self.teacher,
            {
                "title": "Lesson Worksheet",
                "category": "worksheet",
                "file": uploaded_file,
            },
        )

        with (
            patch(
                "core.views.get_object_or_404",
                return_value=self.lesson,
            ),
            patch("core.views.Handout.objects.create") as create_handout,
            patch("core.views.messages.success"),
            patch("core.views.messages.error"),
        ):
            response = add_teacher_lesson_handout(
                request,
                lesson_id=self.lesson.id,
            )

        self.assertEqual(response.status_code, 302)
        create_handout.assert_called_once()
        saved = create_handout.call_args.kwargs
        self.assertIs(saved["lesson"], self.lesson)
        self.assertIsNone(saved["module"])
        self.assertEqual(saved["category"], "worksheet")
        self.assertEqual(saved["title"], "Lesson Worksheet")

    def test_other_teacher_cannot_create_lesson_handout(self):
        uploaded_file = SimpleUploadedFile(
            "worksheet.pdf",
            b"test PDF content",
        )
        request = self.make_request(
            self.other_teacher,
            {
                "title": "Unauthorized Resource",
                "category": "worksheet",
                "file": uploaded_file,
            },
        )

        with (
            patch(
                "core.views.get_object_or_404",
                return_value=self.lesson,
            ),
            patch("core.views.Handout.objects.create") as create_handout,
        ):
            response = add_teacher_lesson_handout(
                request,
                lesson_id=self.lesson.id,
            )

        self.assertEqual(response.status_code, 403)
        create_handout.assert_not_called()

    def test_invalid_category_is_rejected(self):
        uploaded_file = SimpleUploadedFile(
            "worksheet.pdf",
            b"test PDF content",
        )
        request = self.make_request(
            self.teacher,
            {
                "title": "Invalid Category",
                "category": "not_a_valid_category",
                "file": uploaded_file,
            },
        )

        with (
            patch(
                "core.views.get_object_or_404",
                return_value=self.lesson,
            ),
            patch("core.views.Handout.objects.create") as create_handout,
            patch("core.views.messages.error"),
        ):
            response = add_teacher_lesson_handout(
                request,
                lesson_id=self.lesson.id,
            )

        self.assertEqual(response.status_code, 302)
        create_handout.assert_not_called()

    def test_teacher_can_edit_category_without_replacing_file(self):
        existing_file = "handouts/original.pdf"
        handout = SimpleNamespace(
            id=15,
            lesson=self.lesson,
            title="Original Title",
            category="worksheet",
            file=existing_file,
            save=Mock(),
        )
        request = self.make_request(
            self.teacher,
            {
                "title": "Updated Title",
                "category": "practice_test",
            },
        )

        with (
            patch(
                "core.views.get_object_or_404",
                return_value=handout,
            ),
            patch("core.views.messages.success"),
        ):
            response = edit_teacher_lesson_handout(
                request,
                handout_id=handout.id,
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(handout.title, "Updated Title")
        self.assertEqual(handout.category, "practice_test")
        self.assertEqual(handout.file, existing_file)
        handout.save.assert_called_once_with(
            update_fields=["title", "category"]
        )

    def test_other_teacher_cannot_edit_lesson_handout(self):
        handout = SimpleNamespace(
            id=15,
            lesson=self.lesson,
            title="Original Title",
            category="worksheet",
            file="handouts/original.pdf",
            save=Mock(),
        )
        request = self.make_request(
            self.other_teacher,
            {
                "title": "Unauthorized Change",
                "category": "practice_test",
            },
        )

        with patch(
            "core.views.get_object_or_404",
            return_value=handout,
        ):
            response = edit_teacher_lesson_handout(
                request,
                handout_id=handout.id,
            )

        self.assertEqual(response.status_code, 403)
        handout.save.assert_not_called()

    def test_teacher_can_delete_lesson_handout(self):
        handout = SimpleNamespace(
            id=15,
            lesson=self.lesson,
            title="Temporary Worksheet",
            file=None,
            delete=Mock(),
        )
        request = self.make_request(self.teacher, {})

        with (
            patch(
                "core.views.get_object_or_404",
                return_value=handout,
            ),
            patch("core.views.messages.success"),
        ):
            response = delete_teacher_lesson_handout(
                request,
                handout_id=handout.id,
            )

        self.assertEqual(response.status_code, 302)
        handout.delete.assert_called_once()

    def test_other_teacher_cannot_delete_lesson_handout(self):
        handout = SimpleNamespace(
            id=15,
            lesson=self.lesson,
            title="Protected Worksheet",
            file=None,
            delete=Mock(),
        )
        request = self.make_request(self.other_teacher, {})

        with patch(
            "core.views.get_object_or_404",
            return_value=handout,
        ):
            response = delete_teacher_lesson_handout(
                request,
                handout_id=handout.id,
            )

        self.assertEqual(response.status_code, 403)
        handout.delete.assert_not_called()
