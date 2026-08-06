from core.models import Achievement
from core.models import StudentProfile
from core.services.xp_service import add_xp


def award(student, title):

    profile = student.profile

    achievement = Achievement.objects.get(
        title=title
    )

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