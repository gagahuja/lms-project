from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from .models import User
from .models import Course
from .models import Enrollment
from .models import LiveClass
from .models import Attendance


def login_view(request):
    error = None

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            error = "Invalid username or password"

    return render(request, 'login.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('login')



def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if request.user.user_type == 'teacher':
        courses = Course.objects.filter(teacher=request.user)
        return render(request, 'teacher_dashboard.html', {'courses': courses})
    else:
        enrolled = Enrollment.objects.filter(student=request.user)
        enrolled_courses = [e.course for e in enrolled]

        courses = Course.objects.exclude(id__in=[c.id for c in enrolled_courses])

        live_classes = LiveClass.objects.filter(course__in=enrolled_courses)

        return render(request, 'student_dashboard.html', {
            'courses': courses,
            'enrolled_courses': enrolled_courses,
            'live_classes': live_classes
        })
    


def enroll(request, course_id):
    if not request.user.is_authenticated:
        return redirect('login')

    course = Course.objects.get(id=course_id)

    Enrollment.objects.get_or_create(
        student=request.user,
        course=course
    )

    return redirect('dashboard')



def join_class(request, class_id):
    if not request.user.is_authenticated:
        return redirect('login')

    live_class = LiveClass.objects.get(id=class_id)

    Attendance.objects.get_or_create(
        student=request.user,
        live_class=live_class
    )

    return render(request, 'join_class.html', {'class': live_class})