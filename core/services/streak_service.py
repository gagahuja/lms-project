from datetime import date, timedelta

from core.models import StudentProfile


def update_streak(student):

    profile, created = StudentProfile.objects.get_or_create(
        student=student
    )

    today = date.today()

    if profile.last_login_date is None:

        profile.streak = 1
        profile.longest_streak = 1

    elif profile.last_login_date == today:

        return

    elif profile.last_login_date == today - timedelta(days=1):

        profile.streak += 1

    else:

        profile.streak = 1

    profile.longest_streak = max(
        profile.longest_streak,
        profile.streak
    )

    profile.last_login_date = today

    profile.save()