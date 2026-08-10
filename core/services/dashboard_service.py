from django.db.models import Avg, Max, Min, Sum
from django.utils import timezone


from core.models import (
    Course,
    Enrollment,
    Assignment,
    Submission,
    LiveClass,
    Attendance,
    Recording,
    Notification,
    Progress,
    Lesson,
    User,
)


def build_teacher_dashboard(user):

    courses = (
        Course.objects
        .filter(teacher=user)
        .prefetch_related(
            "modules",
            "modules__lessons",
            "modules__lessons__assignments",
        )
    )

    students = (
        User.objects.filter(
            enrollment__course__in=courses,
            user_type="student",
        )
        .distinct()
    )

    assignments = Assignment.objects.filter(
        lesson__module__course__in=courses
    )

    submissions = Submission.objects.filter(
        assignment__lesson__module__course__in=courses
    )

    live_classes = (
        LiveClass.objects.filter(
            course__in=courses
        )
        .order_by("-date")
    )

    teacher_recordings = (
        Recording.objects.filter(
            live_class__course__in=courses
        )
        .select_related(
            "live_class",
            "live_class__course",
        )
        .order_by("-uploaded_at")
    )

    notifications = (
        Notification.objects.filter(
            user=user
        )
        .order_by("-created_at")[:10]
    )

    total_courses = courses.count()

    total_students = students.count()

    total_classes = live_classes.count()

    total_assignments = assignments.count()

    total_submissions = submissions.count()

    pending_reviews = submissions.filter(
        status="submitted"
    ).count()

    pending_submissions = pending_reviews

    checked = submissions.filter(
        status="checked",
        marks__isnull=False
    )

    average_marks = round(
        checked.aggregate(
            Avg("marks")
        )["marks__avg"] or 0,
        1,
    )

    total_revenue = (
        Enrollment.objects.filter(
            course__in=courses
        ).aggregate(
            revenue=Sum("course__price")
        )["revenue"] or 0
    )

    total_live_classes = live_classes.count()

    attendance_records = Attendance.objects.filter(
        live_class__course__in=courses
    )

    attendance_percentage = 0

    if total_live_classes:

        attendance_percentage = round(
            attendance_records.count()
            * 100
            / total_live_classes
        )

    context = {

        "courses": courses,

        "students": students,

        "assignments": assignments,

        "submissions": submissions,

        "live_classes": live_classes,

        "teacher_recordings": teacher_recordings,

        "notifications": notifications,

        "total_courses": total_courses,

        "total_students": total_students,

        "total_classes": total_classes,

        "total_assignments": total_assignments,

        "total_submissions": total_submissions,

        "pending_reviews": pending_reviews,

        "pending_submissions": pending_submissions,

        "average_marks": average_marks,

        "attendance_percentage": attendance_percentage,

        "total_revenue": total_revenue,

    }


    # ==========================================
    # Assignment Analytics
    # ==========================================

    assignment_stats = []

    total_enrolled = Enrollment.objects.filter(
        course__in=courses
    ).count()

    for assignment in assignments:

        assignment_submissions = submissions.filter(
            assignment=assignment
        )

        checked_submissions = assignment_submissions.filter(
            status="checked",
            marks__isnull=False
        )

        average = (
            checked_submissions.aggregate(
                Avg("marks")
            )["marks__avg"]
        )

        highest = (
            checked_submissions.aggregate(
                Max("marks")
            )["marks__max"]
        )

        lowest = (
            checked_submissions.aggregate(
                Min("marks")
            )["marks__min"]
        )

        submission_percentage = 0

        if total_enrolled:

            submission_percentage = round(
                assignment_submissions.count()
                * 100
                / total_enrolled
            )

        if average is None:

            difficulty = "Not Enough Data"

        elif average >= 75:

            difficulty = "Easy"

        elif average >= 50:

            difficulty = "Medium"

        else:

            difficulty = "Hard"

        assignment_stats.append({

            "assignment": assignment,

            "submitted": assignment_submissions.count(),

            "checked": checked_submissions.count(),

            "average": (
                round(average, 1)
                if average is not None
                else None
            ),

            "highest": highest,

            "lowest": lowest,

            "submission_percentage":
                submission_percentage,

            "difficulty": difficulty,

        })

    context["assignment_stats"] = assignment_stats

    # ==========================================
    # Top Students
    # ==========================================

    top_students = []

    total_lessons = Lesson.objects.filter(
        module__course__in=courses
    ).count()

    for student in students:

        checked = Submission.objects.filter(
            student=student,
            assignment__lesson__module__course__in=courses,
            status="checked",
            marks__isnull=False
        )

        average = (
            checked.aggregate(
                Avg("marks")
            )["marks__avg"]
            or 0
        )

        completed = Progress.objects.filter(
            student=student,
            lesson__module__course__in=courses,
            completed=True
        ).count()

        progress = 0

        if total_lessons:

            progress = round(
                completed * 100 / total_lessons
            )

        top_students.append({

            "student": student,

            "average": round(
                average,
                1
            ),

            "progress": progress,

        })

    top_students.sort(
        key=lambda x: x["average"],
        reverse=True
    )

    context["top_students"] = top_students[:10]


    # ==========================================
    # Students Needing Attention
    # ==========================================

    attention_students = []

    for student in students:

        completed = Progress.objects.filter(
            student=student,
            lesson__module__course__in=courses,
            completed=True
        ).count()

        progress = 0

        if total_lessons:

            progress = round(
                completed * 100 / total_lessons
            )

        total_student_assignments = Assignment.objects.filter(
            lesson__module__course__in=courses
        ).count()

        submitted = Submission.objects.filter(
            student=student,
            assignment__lesson__module__course__in=courses
        ).count()

        pending = max(
            total_student_assignments - submitted,
            0
        )

        checked = Submission.objects.filter(
            student=student,
            assignment__lesson__module__course__in=courses,
            status="checked",
            marks__isnull=False
        )

        average = (
            checked.aggregate(
                Avg("marks")
            )["marks__avg"]
            or 0
        )

        if (
            progress < 50
            or pending > 3
            or average < 40
        ):

            attention_students.append({

                "student": student,

                "progress": progress,

                "pending": pending,

                "average": round(
                    average,
                    1
                )

            })

    context["attention_students"] = attention_students

    # ==========================================
    # Recent Activity Feed
    # ==========================================

    activity_feed = []

    recent_submissions = (
        Submission.objects.filter(
            assignment__lesson__module__course__in=courses
        )
        .select_related(
            "student",
            "assignment"
        )
        .order_by("-submitted_at")[:10]
    )

    for submission in recent_submissions:

        activity_feed.append({

            "icon": "📝",

            "message":
                f"{submission.student.username} submitted "
                f"{submission.assignment.title}",

            "time": submission.submitted_at

        })

    recent_reviews = (
        Submission.objects.filter(
            assignment__lesson__module__course__in=courses,
            status="checked",
            reviewed_at__isnull=False
        )
        .select_related(
            "student",
            "assignment"
        )
        .order_by("-reviewed_at")[:10]
    )

    for review in recent_reviews:

        activity_feed.append({

            "icon": "✅",

            "message":
                f"{review.assignment.title} checked for "
                f"{review.student.username}",

            "time": review.reviewed_at

        })

    activity_feed.sort(
        key=lambda x: x["time"],
        reverse=True
    )

    context["activity_feed"] = activity_feed[:15]

    return context



def build_student_dashboard(user):

    enrollments = (
        Enrollment.objects
        .filter(student=user)
        .select_related("course")
    )

    courses = Course.objects.filter(
        enrollment__student=user
    ).distinct()

    live_classes = (
        LiveClass.objects
        .filter(course__in=courses)
        .order_by("date")
    )

    submissions = Submission.objects.filter(
        student=user
    )

    notifications = (
        Notification.objects
        .filter(user=user)
        .order_by("-created_at")[:10]
    )

    profile = getattr(
        user,
        "profile",
        None
    )

    context = {

        "courses": courses,

        "enrollments": enrollments,

        "live_classes": live_classes,

        "assignment_count": submissions.count(),

        "notifications": notifications,

        "profile": profile,

    }

    return context