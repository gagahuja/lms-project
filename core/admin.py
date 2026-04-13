from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User
from .models import Course
from .models import Enrollment
from .models import LiveClass, Attendance
from .models import Module, Lesson, Assignment, Submission
from .models import Quiz, Question, StudentAnswer
from .models import QuizResult
from .models import Handout
from .models import Recording
from .models import CourseRequest



class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'email', 'user_type', 'is_staff']

    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('user_type',)}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('user_type',)}),
    )


class HandoutAdmin(admin.ModelAdmin):
    list_display = ['title', 'lesson', 'created_at']

admin.site.register(Handout, HandoutAdmin)


class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'lesson']

class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['assignment', 'student', 'submitted_at']


class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course']

admin.site.register(Enrollment, EnrollmentAdmin)
admin.site.register(Assignment, AssignmentAdmin)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Course)
#admin.site.register(Enrollment)
admin.site.register(LiveClass)
admin.site.register(Attendance)
admin.site.register(Module)
admin.site.register(Lesson)
#admin.site.register(Assignment)
admin.site.register(Submission, SubmissionAdmin)
admin.site.register(Quiz)
admin.site.register(Question)
admin.site.register(StudentAnswer)
admin.site.register(QuizResult)
admin.site.register(Recording)
admin.site.register(CourseRequest)