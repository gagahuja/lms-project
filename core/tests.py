import hashlib
import hmac
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, SimpleTestCase, override_settings

from core.models import Handout
from core.views import (
    HANDOUT_MAX_FILE_SIZE,
    _check_refund_total_and_alert,
    _handout_upload_error,
    _mark_payment_refunded_if_fully_refunded,
    add_teacher_lesson_handout,
    edit_teacher_lesson_handout,
    delete_teacher_lesson_handout,
    payment_success,
    razorpay_webhook,
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



class RazorpayWebhookPaymentStateTests(SimpleTestCase):
    """Guard successful payment states against delayed failure events."""

    def test_delayed_failed_event_does_not_downgrade_captured_or_refunded(self):
        secret = "test-webhook-secret"

        payload = {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test_delayed_failure",
                        "order_id": "order_test_delayed_failure",
                        "amount": 15000,
                        "currency": "INR",
                    }
                }
            },
        }

        body = json.dumps(payload).encode("utf-8")
        signature = hmac.new(
            secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        for initial_status in ("captured", "refunded"):
            with self.subTest(initial_status=initial_status):
                payment_transaction = SimpleNamespace(
                    pk=123,
                    status=initial_status,
                    amount=15000,
                    currency="INR",
                    save=Mock(),
                )

                duplicate_events = Mock()
                duplicate_events.exists.return_value = False

                order_transactions = Mock()
                order_transactions.first.return_value = payment_transaction

                def filter_side_effect(**kwargs):
                    if "razorpay_event_id" in kwargs:
                        return duplicate_events
                    if "razorpay_order_id" in kwargs:
                        return order_transactions
                    self.fail(f"Unexpected transaction filter: {kwargs}")

                locking_queryset = Mock()
                locking_queryset.get.return_value = payment_transaction

                request = RequestFactory().generic(
                    "POST",
                    "/webhook/",
                    data=body,
                    content_type="application/json",
                    HTTP_X_RAZORPAY_SIGNATURE=signature,
                    HTTP_X_RAZORPAY_EVENT_ID=(
                        f"evt_delayed_failure_{initial_status}"
                    ),
                )

                with (
                    override_settings(
                        RAZORPAY_WEBHOOK_SECRET=secret
                    ),
                    patch(
                        "core.views.PaymentTransaction.objects.filter",
                        side_effect=filter_side_effect,
                    ),
                    patch(
                        "core.views.PaymentTransaction.objects.select_for_update",
                        return_value=locking_queryset,
                    ),
                    patch("core.views.transaction.atomic"),
                ):
                    response = razorpay_webhook(request)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    payment_transaction.status,
                    initial_status,
                )
                payment_transaction.save.assert_not_called()

class FullRefundStateTests(SimpleTestCase):
    """Test when a payment should be marked fully refunded."""

    def make_payment_transaction(
        self, status, amount, processed_refund_amounts
    ):
        processed_total = sum(processed_refund_amounts)

        refunds = Mock()
        processed_refunds = Mock()
        processed_refunds.aggregate.return_value = {
            "total": processed_total
        }
        refunds.filter.return_value = processed_refunds

        return SimpleNamespace(
            status=status,
            amount=amount,
            refunds=refunds,
            save=Mock(),
        )

    def test_partial_refund_does_not_mark_payment_refunded(self):
        payment = self.make_payment_transaction(
            status="captured",
            amount=10000,
            processed_refund_amounts=[4000],
        )

        _mark_payment_refunded_if_fully_refunded(payment)

        self.assertEqual(payment.status, "captured")
        payment.save.assert_not_called()

    def test_full_refund_marks_payment_refunded(self):
        payment = self.make_payment_transaction(
            status="captured",
            amount=10000,
            processed_refund_amounts=[10000],
        )

        _mark_payment_refunded_if_fully_refunded(payment)

        self.assertEqual(payment.status, "refunded")
        payment.save.assert_called_once_with(
            update_fields=["status"]
        )

    def test_multiple_processed_refunds_can_complete_full_refund(self):
        payment = self.make_payment_transaction(
            status="captured",
            amount=10000,
            processed_refund_amounts=[2500, 3500, 4000],
        )

        _mark_payment_refunded_if_fully_refunded(payment)

        self.assertEqual(payment.status, "refunded")
        payment.save.assert_called_once_with(
            update_fields=["status"]
        )

    def test_already_refunded_payment_is_not_saved_again(self):
        payment = self.make_payment_transaction(
            status="refunded",
            amount=10000,
            processed_refund_amounts=[10000],
        )

        _mark_payment_refunded_if_fully_refunded(payment)

        self.assertEqual(payment.status, "refunded")
        payment.save.assert_not_called()
        payment.refunds.filter.assert_not_called()

class RazorpayCapturedWebhookRefundGuardTests(SimpleTestCase):
    """Ensure a captured webhook cannot undo a full refund."""

    def test_captured_event_does_not_downgrade_refunded_payment(self):
        secret = "test-webhook-secret"
        event_id = "evt_captured_after_refund"
        order_id = "order_test_captured_after_refund"

        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test_captured_after_refund",
                        "order_id": order_id,
                        "amount": 15000,
                        "currency": "INR",
                        "notes": {
                            "course_id": "7",
                            "user_id": "42",
                        },
                    }
                }
            },
        }

        body = json.dumps(payload).encode("utf-8")
        signature = hmac.new(
            secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        request = RequestFactory().generic(
            "POST",
            "/webhook/",
            data=body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=signature,
            HTTP_X_RAZORPAY_EVENT_ID=event_id,
        )

        payment_transaction = SimpleNamespace(
            pk=987,
            status="refunded",
            student_id=42,
            course_id=7,
            amount=15000,
            currency="INR",
            student=SimpleNamespace(username="teststudent"),
            course=SimpleNamespace(id=7),
            save=Mock(),
        )

        duplicate_events = Mock()
        duplicate_events.exists.return_value = False

        def filter_side_effect(**kwargs):
            if kwargs == {"razorpay_event_id": event_id}:
                return duplicate_events
            self.fail(f"Unexpected transaction filter: {kwargs}")

        transaction_lookup = Mock()
        transaction_lookup.filter.return_value.first.return_value = (
            payment_transaction
        )

        locking_queryset = Mock()
        locking_queryset.get.return_value = payment_transaction

        razorpay_client = Mock()
        razorpay_client.order.fetch.return_value = {
            "amount": 15000,
            "currency": "INR",
            "notes": {
                "course_id": "7",
                "user_id": "42",
            },
        }

        with (
            override_settings(
                RAZORPAY_WEBHOOK_SECRET=secret,
                RAZORPAY_KEY="test-key",
                RAZORPAY_SECRET="test-secret",
            ),
            patch(
                "core.views.PaymentTransaction.objects.filter",
                side_effect=filter_side_effect,
            ),
            patch(
                "core.views.PaymentTransaction.objects.select_related",
                return_value=transaction_lookup,
            ),
            patch(
                "core.views.PaymentTransaction.objects.select_for_update",
                return_value=locking_queryset,
            ),
            patch(
                "core.views.razorpay.Client",
                return_value=razorpay_client,
            ),
            patch("core.views.transaction.atomic"),
            patch(
                "core.views.Enrollment.objects.get_or_create"
            ) as enrollment_get_or_create,
        ):
            response = razorpay_webhook(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payment_transaction.status, "refunded")
        payment_transaction.save.assert_not_called()
        enrollment_get_or_create.assert_not_called()
        locking_queryset.get.assert_called_once_with(pk=987)

class PaymentSuccessRefundGuardTests(SimpleTestCase):
    """Ensure browser confirmation cannot undo a full refund."""

    def test_late_confirmation_does_not_downgrade_refunded_payment(self):
        course = SimpleNamespace(
            id=7,
            price=150,
        )

        payment_transaction = SimpleNamespace(
            pk=456,
            status="refunded",
            amount=15000,
            save=Mock(),
        )

        user = SimpleNamespace(
            id=42,
            is_authenticated=True,
        )

        request = RequestFactory().post(
            "/payment-success/7/",
            {
                "razorpay_payment_id": "pay_test_refunded",
                "razorpay_order_id": "order_test_refunded",
                "razorpay_signature": "test-signature",
            },
        )
        request.user = user

        client = Mock()
        client.order.fetch.return_value = {
            "amount": 15000,
            "notes": {
                "course_id": "7",
                "user_id": "42",
            },
        }
        client.payment.fetch.return_value = {
            "order_id": "order_test_refunded",
            "status": "captured",
        }

        locking_queryset = Mock()
        locking_queryset.get.return_value = payment_transaction

        with (
            override_settings(
                RAZORPAY_KEY="test-key",
                RAZORPAY_SECRET="test-secret",
            ),
            patch(
                "core.views.get_object_or_404",
                side_effect=[course, payment_transaction],
            ),
            patch(
                "core.views.razorpay.Client",
                return_value=client,
            ),
            patch(
                "core.views.PaymentTransaction.objects.select_for_update",
                return_value=locking_queryset,
            ),
            patch("core.views.transaction.atomic"),
            patch(
                "core.views.Enrollment.objects.get_or_create"
            ) as enrollment_get_or_create,
            patch("core.views.messages.error") as message_error,
        ):
            response = payment_success(request, 7)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(payment_transaction.status, "refunded")
        payment_transaction.save.assert_not_called()
        enrollment_get_or_create.assert_not_called()
        message_error.assert_called_once()
        locking_queryset.get.assert_called_once_with(pk=456)


class RefundOverageAlertTests(SimpleTestCase):
    """Test the refund total alert without database access."""

    def make_test_objects(self, current_amount, current_status,
                          other_refund_total, original_amount=10000):
        current_refund = SimpleNamespace(
            pk=2,
            amount=current_amount,
            status=current_status,
        )

        refunds = Mock()
        refunds.exclude.return_value.filter.return_value.aggregate.return_value = {
            "total": other_refund_total
        }

        payment = SimpleNamespace(
            amount=original_amount,
            refunds=refunds,
            razorpay_payment_id="pay_test_123",
            currency="INR",
        )

        return payment, current_refund

    def test_alerts_when_refunds_exceed_original_payment(self):
        payment, refund = self.make_test_objects(
            current_amount=6000,
            current_status="processed",
            other_refund_total=5000,
        )

        with patch("core.views.logger.critical") as critical:
            total = _check_refund_total_and_alert(payment, refund)

        self.assertEqual(total, 11000)
        critical.assert_called_once()

    def test_no_alert_when_refunds_are_within_payment_amount(self):
        payment, refund = self.make_test_objects(
            current_amount=4000,
            current_status="processed",
            other_refund_total=5000,
        )

        with patch("core.views.logger.critical") as critical:
            total = _check_refund_total_and_alert(payment, refund)

        self.assertEqual(total, 9000)
        critical.assert_not_called()

    def test_failed_refund_is_not_counted(self):
        payment, refund = self.make_test_objects(
            current_amount=7000,
            current_status="failed",
            other_refund_total=5000,
        )

        with patch("core.views.logger.critical") as critical:
            total = _check_refund_total_and_alert(payment, refund)

        self.assertEqual(total, 5000)
        critical.assert_not_called()


class RazorpayInvalidRefundAmountTests(SimpleTestCase):
    """Reject invalid refund amounts before recording a refund."""

    def test_invalid_refund_amounts_are_rejected(self):
        secret = "test-webhook-secret"
        invalid_amounts = [0, -100, 12.5, "100", True, False]

        for amount in invalid_amounts:
            with self.subTest(amount=amount):
                payload = {
                    "event": "refund.processed",
                    "payload": {
                        "refund": {
                            "entity": {
                                "id": "rfnd_test_invalid_amount",
                                "payment_id": "pay_test_invalid_amount",
                                "amount": amount,
                                "currency": "INR",
                            }
                        }
                    },
                }

                body = json.dumps(payload).encode("utf-8")
                signature = hmac.new(
                    secret.encode("utf-8"),
                    body,
                    hashlib.sha256,
                ).hexdigest()

                request = RequestFactory().generic(
                    "POST",
                    "/webhook/",
                    data=body,
                    content_type="application/json",
                    HTTP_X_RAZORPAY_SIGNATURE=signature,
                    HTTP_X_RAZORPAY_EVENT_ID=(
                        f"evt_invalid_amount_{type(amount).__name__}_{invalid_amounts.index(amount)}"
                    ),
                )

                with (
                    override_settings(
                        RAZORPAY_WEBHOOK_SECRET=secret
                    ),
                    patch(
                        "core.views.PaymentTransaction.objects.filter"
                    ) as transaction_filter,
                    patch(
                        "core.views.Refund.objects.filter"
                    ) as refund_filter,
                    patch(
                        "core.views.Refund.objects.create"
                    ) as refund_create,
                ):
                    refund_filter.return_value.exists.return_value = False

                    response = razorpay_webhook(request)

                self.assertEqual(response.status_code, 400)
                transaction_filter.assert_not_called()
                refund_create.assert_not_called()
