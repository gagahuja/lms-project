from datetime import timedelta

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
    QuizResult,
    StudentProfile,
    User,
)

from core.services.streak_service import update_streak
from core.services.quiz_analytics_service import get_quiz_analytics
from core.services.ai_feedback_service import generate_recommendations


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
            course__in=courses,
            is_completed=False
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

    # =========================================================
    # UPDATE DAILY STREAK
    # =========================================================

    update_streak(user)


    # =========================================================
    # ENROLLED COURSES
    # =========================================================

    enrollments = (
        Enrollment.objects
        .filter(student=user)
        .select_related("course")
    )

    enrolled_courses = [
        enrollment.course
        for enrollment in enrollments
    ]


    # =========================================================
    # NEXT LIVE CLASS
    # =========================================================

    now = timezone.now()

    next_class = (
        LiveClass.objects
        .filter(
            course__in=enrolled_courses,
            is_live=True
        )
        .order_by("date")
        .first()
    )

    if not next_class:

        next_class = (
            LiveClass.objects
            .filter(
                course__in=enrolled_courses,
                date__gte=now
            )
            .order_by("date")
            .first()
        )


    # =========================================================
    # LIVE CLASSES
    # =========================================================

    thirty_minutes_ago = (
        now - timedelta(minutes=30)
    )

    live_classes = (
        LiveClass.objects
        .filter(
            course__in=enrolled_courses
        )
        .exclude(
            is_completed=True,
            completed_at__lt=thirty_minutes_ago
        )
        .order_by("date")
    )


    # =========================================================
    # LIVE CLASS STATUS
    # =========================================================

    for cls in live_classes:

        cls.can_join = False
        cls.status = "Upcoming"


        # -----------------------------------------------------
        # Starting Soon
        # -----------------------------------------------------

        if (
            cls.date - timedelta(minutes=5)
            <= now
            <= cls.date
        ):

            cls.status = "Starting Soon"


        # -----------------------------------------------------
        # Live
        # -----------------------------------------------------

        if cls.is_live:

            cls.status = "Live"


        # -----------------------------------------------------
        # Completed
        # -----------------------------------------------------

        if (
            cls.is_completed
            or now > cls.date + timedelta(hours=2)
        ):

            cls.status = "Completed"


        # -----------------------------------------------------
        # Join Condition
        # -----------------------------------------------------

        if (
            cls.is_live
            or (
                cls.date - timedelta(minutes=5)
                <= now
                <= cls.date + timedelta(hours=2)
            )
        ):

            cls.can_join = True


    # =========================================================
    # COURSE PROGRESS + SMART CONTINUE LEARNING
    # =========================================================

    progress_data = []


    for course in enrolled_courses:

        # -----------------------------------------------------
        # Get lessons in the correct course order
        # -----------------------------------------------------

        lessons = list(
            Lesson.objects
            .filter(
                module__course=course
            )
            .select_related(
                "module"
            )
            .order_by(
                "module__id",
                "id"
            )
        )


        total_lessons = len(lessons)


        # -----------------------------------------------------
        # Get completed lesson IDs for this student
        # -----------------------------------------------------

        completed_lesson_ids = set(
            Progress.objects
            .filter(
                student=user,
                lesson__module__course=course,
                completed=True
            )
            .values_list(
                "lesson_id",
                flat=True
            )
        )


        completed_lessons = len(
            completed_lesson_ids
        )


        # -----------------------------------------------------
        # Calculate course percentage
        # -----------------------------------------------------

        percent = 0

        if total_lessons > 0:

            percent = int(
                (completed_lessons / total_lessons)
                * 100
            )


        # -----------------------------------------------------
        # Find the FIRST unfinished lesson
        # -----------------------------------------------------

        next_lesson = None

        for lesson in lessons:

            if lesson.id not in completed_lesson_ids:

                next_lesson = lesson

                break


        # -----------------------------------------------------
        # Build Course Topics for Dashboard
        # -----------------------------------------------------

        course_topics = []

        current_module = None
        current_module_data = None

        for lesson in lessons:

            # New module
            if (
                current_module is None
                or lesson.module.id != current_module.id
            ):

                current_module = lesson.module

                current_module_data = {
                    "module": current_module,
                    "lessons": [],
                }

                course_topics.append(
                    current_module_data
                )


            # Lesson status
            lesson_completed = (
                lesson.id in completed_lesson_ids
            )

            lesson_status = "completed"

            if not lesson_completed:

                lesson_status = "next"

                if (
                    next_lesson is None
                    or lesson.id != next_lesson.id
                ):

                    lesson_status = "not_started"


            current_module_data["lessons"].append({

                "lesson": lesson,

                "completed": lesson_completed,

                "is_next": (
                    next_lesson is not None
                    and lesson.id == next_lesson.id
                ),

                "status": lesson_status,

            })

        # -----------------------------------------------------
        # First lesson
        # -----------------------------------------------------

        first_lesson = (
            lessons[0]
            if lessons
            else None
        )


        # -----------------------------------------------------
        # Certificate
        # -----------------------------------------------------

        certificate_unlocked = (
            percent >= 80
        )


        if certificate_unlocked:

            Notification.objects.get_or_create(
                user=user,
                message=(
                    f"🎓 Certificate unlocked for "
                    f"{course.title}"
                )
            )


        # -----------------------------------------------------
        # Dashboard data
        # -----------------------------------------------------

        progress_data.append({

            "course": course,

            "percent": percent,

            "certificate": certificate_unlocked,

            "next_lesson": next_lesson,

            "first_lesson": first_lesson,

            "course_completed": (
                total_lessons > 0
                and completed_lessons == total_lessons
            ),

            "course_topics": course_topics,

        })


    # =========================================================
    # ASSIGNMENTS
    # =========================================================

    assignments = (
        Assignment.objects
        .filter(
            lesson__module__course__in=enrolled_courses
        )
    )


    assignment_data = []


    for assignment in assignments:

        submission = (
            Submission.objects
            .filter(
                assignment=assignment,
                student=user
            )
            .first()
        )


        assignment_data.append({

            "assignment": assignment,

            "submitted": (
                submission is not None
            ),

            "submission": submission,

        })


    # =========================================================
    # QUIZ RESULTS
    # =========================================================

    quiz_results = (
        QuizResult.objects
        .filter(student=user)
        .order_by("-created_at")
    )


    # =========================================================
    # QUIZ PERFORMANCE SNAPSHOT
    # =========================================================

    quiz_analytics = get_quiz_analytics(user)

    quiz_performance = {
        "percentage": quiz_analytics["percentage"],
        "level": quiz_analytics["level"],
        "strongest_topic": quiz_analytics["strongest_topic"],
        "weakest_topic": quiz_analytics["weakest_topic"],
        "topic_performance": quiz_analytics["topic_performance"],
        "quiz_count": len(quiz_analytics["quiz_history"]),
    }

    


    # =========================================================
    # SMART LEARNING RECOMMENDATION
    # =========================================================

    recommendation = None


    # ---------------------------------------------------------
    # GET TOPICS WHERE THE STUDENT MADE ACTUAL MISTAKES
    # ---------------------------------------------------------

    weaknesses = quiz_analytics.get(
        "weaknesses",
        []
    )


    topic_mistakes = {}


    for weakness in weaknesses:

        topic = (
            weakness.get("topic", "")
            .strip()
        )


        if topic:

            topic_mistakes[topic] = (
                topic_mistakes.get(topic, 0) + 1
            )


    # ---------------------------------------------------------
    # FIND THE BEST TOPIC TO RECOMMEND
    # ---------------------------------------------------------

    recommended_topic = None


    if topic_mistakes:

        # Prefer the topic with the highest number of mistakes.
        recommended_topic_name = max(
            topic_mistakes,
            key=topic_mistakes.get
        )


        # Find performance information for this topic.

        for item in quiz_performance.get(
            "topic_performance",
            []
        ):

            if item.get("topic") == recommended_topic_name:

                recommended_topic = item
                break


    # ---------------------------------------------------------
    # FIND MATCHING LESSON
    # ---------------------------------------------------------

    if recommended_topic:

        topic_name = (
            recommended_topic.get("topic", "")
            .strip()
        )


        topic_percentage = (
            recommended_topic.get("percentage", 0)
        )


        lessons = (
            Lesson.objects
            .filter(
                module__course__in=enrolled_courses
            )
            .select_related(
                "module",
                "module__course"
            )
            .order_by(
                "module__course__id",
                "module__id",
                "id"
            )
        )


        matching_lesson = None


        topic_words = {
            word.lower()
            for word in topic_name.split()
            if len(word) >= 3
        }


        for lesson in lessons:

            lesson_text = (
                f"{lesson.title} "
                f"{lesson.module.title}"
            ).lower()


            if topic_words and all(
                word in lesson_text
                for word in topic_words
            ):

                matching_lesson = lesson
                break


        # -----------------------------------------------------
        # FINAL RECOMMENDATION
        # -----------------------------------------------------

        recommendation = {

            "topic":
                topic_name,

            "percentage":
                topic_percentage,

            "lesson":
                matching_lesson,

            "has_lesson":
                matching_lesson is not None,

            "mistakes":
                topic_mistakes.get(
                    topic_name,
                    0
                ),

        }

    # =========================================================
    # CLASS RECORDINGS
    # =========================================================

    recordings = (
        Recording.objects
        .filter(
            live_class__course__in=enrolled_courses
        )
        .select_related(
            "live_class",
            "live_class__course"
        )
        .order_by("-uploaded_at")
    )


    # =========================================================
    # NOTIFICATIONS
    # =========================================================

    notifications = (
        Notification.objects
        .filter(user=user)
        .order_by("-created_at")[:5]
    )


    notification_count = (
        Notification.objects
        .filter(
            user=user,
            is_read=False
        )
        .count()
    )


    # =========================================================
    # STUDENT PROFILE
    # =========================================================

    profile, created = (
        StudentProfile.objects
        .prefetch_related(
            "achievements"
        )
        .get_or_create(
            student=user
        )
    )


    # =========================================================
    # STUDENT ACHIEVEMENTS
    # =========================================================

    achievements = (
        profile.achievements
        .all()
        .order_by("title")
    )

    # =========================================================
    # FINAL CONTEXT
    # =========================================================

    context = {

        # Courses
        "enrolled_courses":
            enrolled_courses,

        "courses":
            enrolled_courses,

        "enrollments":
            enrollments,


        # Progress
        "progress_data":
            progress_data,


        # Live Classes
        "live_classes":
            live_classes,

        "next_class":
            next_class,


        # Assignments
        "assignments":
            assignment_data,

        "assignment_count":
            len(assignment_data),


        # Quizzes
        "quiz_results":
            quiz_results,

        "quiz_performance":
            quiz_performance,

        "recommendation":
            recommendation,


        # Recordings
        "recordings":
            recordings,


        # Notifications
        "notifications":
            notifications,

        "notification_count":
            notification_count,


        # Profile
        "profile":
            profile,


        # Achievements
        "achievements":
            achievements,

    }


    return context