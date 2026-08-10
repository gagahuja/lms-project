from django.db.models import Avg

from core.models import (
    Course,
    Enrollment,
    Assignment,
    Submission,
    LiveClass,
    Recording,
)


def teacher_stats(user):

    courses = Course.objects.filter(
        teacher=user
    )

    students = Enrollment.objects.filter(
        course__in=courses
    )

    submissions = Submission.objects.filter(
        assignment__lesson__module__course__in=courses
    )

    return {

        "courses": courses,

        "students": students,

        "submissions": submissions,

        "total_courses": courses.count(),

        "total_students": students.count(),

        "total_assignments":
            Assignment.objects.filter(
                lesson__module__course__in=courses
            ).count(),

        "total_live_classes":
            LiveClass.objects.filter(
                course__in=courses
            ).count(),

        "total_recordings":
            Recording.objects.filter(
                live_class__course__in=courses
            ).count(),

        "total_submissions":
            submissions.count(),

        "pending_reviews":
            submissions.filter(
                status="submitted"
            ).count(),

        "average_marks":
            submissions.filter(
                marks__isnull=False
            ).aggregate(
                Avg("marks")
            )["marks__avg"] or 0,

    }