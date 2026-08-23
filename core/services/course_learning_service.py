from django.db.models import Prefetch

from core.models import (
    Course,
    Enrollment,
    Module,
    Lesson,
    Progress,
    Quiz,
    QuizResult,
)


def build_course_learning_context(user, course):
    """
    Build the complete learning context for a student's
    course overview page.

    This service keeps course-learning logic out of views.py.
    """

    # =========================================================
    # ENROLLMENT
    # =========================================================

    is_enrolled = Enrollment.objects.filter(
        student=user,
        course=course
    ).exists()

    # =========================================================
    # COMPLETED LESSONS
    # =========================================================

    completed_lesson_ids = set(
        Progress.objects.filter(
            student=user,
            lesson__module__course=course,
            completed=True
        ).values_list(
            "lesson_id",
            flat=True
        )
    )

    # =========================================================
    # MODULES + LESSONS
    # =========================================================

    lessons_queryset = Lesson.objects.all().prefetch_related(
        "assignments",
        "handout_set",
    )

    modules = (
        Module.objects.filter(
            course=course
        )
        .prefetch_related(
            Prefetch(
                "lessons",
                queryset=lessons_queryset
            )
        )
        .order_by("id")
    )

    # =========================================================
    # TOTAL LESSONS
    # =========================================================

    total_lessons = 0
    completed_lessons = 0

    first_lesson = None
    next_lesson = None

    # =========================================================
    # PREPARE LESSON STATUS
    # =========================================================

    for module in modules:

        for lesson in module.lessons.all():

            total_lessons += 1

            lesson.is_completed = (
                lesson.id in completed_lesson_ids
            )

            if lesson.is_completed:
                completed_lessons += 1

            # First lesson in the course
            if first_lesson is None:
                first_lesson = lesson

            # First incomplete lesson
            if (
                next_lesson is None
                and not lesson.is_completed
            ):
                next_lesson = lesson

    # =========================================================
    # COURSE PROGRESS
    # =========================================================

    progress = 0

    if total_lessons > 0:
        progress = round(
            completed_lessons * 100 / total_lessons
        )

    # =========================================================
    # COURSE COMPLETION
    # =========================================================

    course_completed = (
        total_lessons > 0
        and completed_lessons == total_lessons
    )

    # =========================================================
    # IF COURSE IS COMPLETE
    # =========================================================

    if course_completed:
        next_lesson = None

    # =========================================================
    # QUIZZES + STUDENT PERFORMANCE
    # =========================================================

    quizzes = Quiz.objects.filter(
        course=course
    ).order_by("id")

    # ---------------------------------------------------------
    # Get all quiz attempts made by this student
    # ---------------------------------------------------------

    quiz_results = (
        QuizResult.objects
        .filter(
            student=user,
            quiz__course=course
        )
        .select_related("quiz")
        .order_by(
            "quiz_id",
            "-created_at"
        )
    )

    # ---------------------------------------------------------
    # Organise attempts by quiz
    # ---------------------------------------------------------

    quiz_attempts = {}

    for result in quiz_results:

        quiz_id = result.quiz_id

        if quiz_id not in quiz_attempts:
            quiz_attempts[quiz_id] = []

        quiz_attempts[quiz_id].append(result)

    # ---------------------------------------------------------
    # Attach performance information to each quiz
    # ---------------------------------------------------------

    for quiz in quizzes:

        attempts = quiz_attempts.get(
            quiz.id,
            []
        )

        quiz.attempted = bool(attempts)

        quiz.attempt_count = len(attempts)

        quiz.latest_result = (
            attempts[0]
            if attempts
            else None
        )

        # -----------------------------------------------------
        # Find best attempt
        # -----------------------------------------------------

        best_result = None
        best_percentage = 0

        for result in attempts:

            if result.total:

                percentage = round(
                    (result.score / result.total) * 100
                )

            else:

                percentage = 0

            if (
                best_result is None
                or percentage > best_percentage
            ):

                best_result = result
                best_percentage = percentage

        quiz.best_result = best_result

        quiz.best_percentage = best_percentage

    # =========================================================
    # RETURN CONTEXT
    # =========================================================

    return {
        "course": course,

        "modules": modules,

        "quizzes": quizzes,

        "is_enrolled": is_enrolled,

        "total_lessons": total_lessons,

        "completed_lessons": completed_lessons,

        "progress": progress,

        "course_completed": course_completed,

        "first_lesson": first_lesson,

        "next_lesson": next_lesson,
    }



def get_lesson_learning_context(user, lesson_id):
    """
    Build the learning context for an individual lesson.
    """

    lesson = (
        Lesson.objects
        .select_related(
            "module",
            "module__course"
        )
        .prefetch_related(
            "assignments",
            "handout_set"
        )
        .filter(
            id=lesson_id
        )
        .first()
    )

    if lesson is None:
        return None

    course = lesson.module.course

    # =========================================================
    # ACCESS CHECK
    # =========================================================

    is_enrolled = Enrollment.objects.filter(
        student=user,
        course=course
    ).exists()

    # =========================================================
    # COMPLETION STATUS
    # =========================================================

    progress = Progress.objects.filter(
        student=user,
        lesson=lesson
    ).first()

    is_completed = (
        progress is not None
        and progress.completed
    )

    # =========================================================
    # COURSE PROGRESS
    # =========================================================

    total_course_lessons = Lesson.objects.filter(
        module__course=course
    ).count()

    completed_course_lessons = Progress.objects.filter(
        student=user,
        lesson__module__course=course,
        completed=True
    ).count()

    course_progress = 0

    if total_course_lessons > 0:
        course_progress = round(
            completed_course_lessons * 100
            / total_course_lessons
        )

    # =========================================================
    # ALL COURSE LESSONS
    # =========================================================

    lessons = list(
        Lesson.objects.filter(
            module__course=course
        )
        .select_related("module")
        .order_by("module__id", "id")
    )

    current_index = None

    for index, current_lesson in enumerate(lessons):

        if current_lesson.id == lesson.id:
            current_index = index
            break

    previous_lesson = None
    next_lesson = None

    if current_index is not None:

        if current_index > 0:
            previous_lesson = lessons[
                current_index - 1
            ]

        if current_index < len(lessons) - 1:
            next_lesson = lessons[
                current_index + 1
            ]

    # =========================================================
    # RETURN CONTEXT
    # =========================================================

    return {
        "lesson": lesson,
        "course": course,
        "module": lesson.module,

        "is_enrolled": is_enrolled,
        "is_completed": is_completed,

        "previous_lesson": previous_lesson,
        "next_lesson": next_lesson,

        "total_lessons": len(lessons),

        "current_position": (
            current_index + 1
            if current_index is not None
            else None
        ),

        "course_progress": course_progress,
        "completed_course_lessons": completed_course_lessons,
        "total_course_lessons": total_course_lessons,
    }