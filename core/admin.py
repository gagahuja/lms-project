from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User
from .models import Course
from .models import Enrollment
from .models import LiveClass, Attendance

class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'email', 'user_type', 'is_staff']

    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('user_type',)}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('user_type',)}),
    )

admin.site.register(User, CustomUserAdmin)
admin.site.register(Course)
admin.site.register(Enrollment)
admin.site.register(LiveClass)
admin.site.register(Attendance)