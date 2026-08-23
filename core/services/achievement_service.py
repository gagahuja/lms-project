from core.models import Achievement
from core.models import StudentProfile
from core.services.xp_service import add_xp


def award(student, title):

    profile, created = StudentProfile.objects.get_or_create(
        student=student
    )

    achievement = Achievement.objects.filter(
        title=title
    ).first()

    if not achievement:
        return False

    if profile.achievements.filter(
        id=achievement.id
    ).exists():

        return False

    profile.achievements.add(
        achievement
    )

    if achievement.xp_reward:

        add_xp(
            student,
            achievement.xp_reward
        )

    return True