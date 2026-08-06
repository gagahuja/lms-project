from django.contrib.auth import get_user_model
from django.db.models import Avg, Value
from django.db.models.functions import Coalesce

User = get_user_model()


def get_student_leaderboard():

    rankings = (
        User.objects
        .filter(user_type="student")
        .annotate(
            average_marks=Coalesce(
                Avg("submissions__marks"),
                Value(0.0)
            )
        )
        .order_by(
            "-average_marks",
            "username"
        )
    )

    leaderboard = []

    for rank, student in enumerate(rankings, start=1):

        leaderboard.append({

            "rank": rank,

            "student": student,

            "average_marks": round(
                student.average_marks or 0,
                1
            ),

        })

    return leaderboard