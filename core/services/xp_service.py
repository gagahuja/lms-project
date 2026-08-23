from core.models import StudentProfile


LEVELS = [
    0,
    100,
    250,
    450,
    700,
    1000,
    1400,
    1900,
    2500,
    3200,
]


def update_level(profile):

    level = 1

    for i, xp in enumerate(LEVELS, start=1):
        if profile.xp >= xp:
            level = i

    profile.level = level
    profile.save(update_fields=["level"])


def add_xp(student, points):

    profile, created = StudentProfile.objects.get_or_create(
        student=student
    )

    profile.xp += points
    profile.save(update_fields=["xp"])

    update_level(profile)