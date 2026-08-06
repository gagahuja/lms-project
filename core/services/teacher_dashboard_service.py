from django.db.models import Avg

from core.models import (
    Course,
    Enrollment,
    Assignment,
    Submission,
    LiveClass,
)


def get_basic_stats(user):
    """
    Basic teacher dashboard statistics.
    """

    courses = Course.objects.filter(
        teacher=user
    ).prefetch_related(
        "modules__lessons__assignments"
    )

    total_students = Enrollment.objects.filter(
        course__in=courses
    ).count()

    total_classes = LiveClass.objects.filter(
        course__in=courses
    ).count()

    total_assignments = Assignment.objects.filter(
        lesson__module__course__in=courses
    ).count()

    total_revenue = total_students * 500

    submissions = Submission.objects.filter(
        assignment__lesson__module__course__in=courses
    )

    total_submissions = submissions.count()

    pending_reviews = submissions.filter(
        status="submitted"
    ).count()

    average_marks = (
        submissions.filter(
            marks__isnull=False
        ).aggregate(
            Avg("marks")
        )["marks__avg"] or 0
    )

    return {
        "courses": courses,
        "total_students": total_students,
        "total_classes": total_classes,
        "total_assignments": total_assignments,
        "total_revenue": total_revenue,
        "total_submissions": total_submissions,
        "pending_reviews": pending_reviews,
        "average_marks": round(average_marks, 1),
    }