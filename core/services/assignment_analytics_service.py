from django.db.models import Avg, Max, Min

from core.models import (
    Assignment,
    Submission,
)


def get_assignment_statistics(courses):

    assignment_stats = []

    assignments = Assignment.objects.filter(
        lesson__module__course__in=courses
    )

    for assignment in assignments:

        submissions = Submission.objects.filter(
            assignment=assignment
        )

        checked = submissions.filter(
            status="checked",
            marks__isnull=False
        )

        avg_marks = None
        highest = None
        lowest = None
        difficulty = "Not Enough Data"

        if checked.exists():

            avg_marks = checked.aggregate(
                Avg("marks")
            )["marks__avg"]

            highest = checked.aggregate(
                Max("marks")
            )["marks__max"]

            lowest = checked.aggregate(
                Min("marks")
            )["marks__min"]

            if avg_marks >= 75:
                difficulty = "Easy"

            elif avg_marks >= 50:
                difficulty = "Medium"

            else:
                difficulty = "Hard"

        assignment_stats.append({

            "assignment": assignment,

            "submitted": submissions.count(),

            "checked": checked.count(),

            "average": round(avg_marks, 1) if avg_marks else None,

            "highest": highest,

            "lowest": lowest,

            "difficulty": difficulty,

        })

    return assignment_stats