from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from .models import User
from .models import Course
from .models import Enrollment
from .models import LiveClass
from .models import Attendance
from .models import Module
from .models import Assignment
from .models import Submission
from django.contrib.auth import get_user_model
from django.db.models import Count
import json
from django.views.decorators.csrf import csrf_exempt
from .models import Quiz, Question, StudentAnswer
from .models import Lesson
from .models import QuizResult


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


def home(request):
    return render(request, 'home.html')


def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if getattr(request.user, 'user_type', None) == 'teacher':
        courses = Course.objects.filter(teacher=request.user)

        total_students = Enrollment.objects.filter(course__in=courses).count()
        total_classes = LiveClass.objects.filter(course__in=courses).count()

        # 📊 GRAPH DATA
        course_names = []
        student_counts = []

        for course in courses:
            course_names.append(course.title)
            count = Enrollment.objects.filter(course=course).count()
            student_counts.append(count)

        # 💰 REVENUE DATA
        total_revenue = 0
        course_revenue = []

        for course in courses:
            enrollments = Enrollment.objects.filter(course=course).count()
            revenue = enrollments * course.price

            total_revenue += revenue

            course_revenue.append({
                'course': course.title,
                'revenue': revenue
            })

        return render(request, 'teacher_dashboard.html', {
            'courses': courses,
            'total_students': total_students,
            'total_classes': total_classes,
            'course_names': json.dumps(course_names),
            'student_counts': json.dumps(student_counts),
            'total_revenue': total_revenue,
            'course_revenue': course_revenue,
        })
    
        
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



#def create_admin(request):
#    User = get_user_model()
#    if not User.objects.filter(username='admin').exists():
#        User.objects.create_superuser('admin', 'admin@gmail.com', 'Admin@123')
#   return HttpResponse("Admin created")



def signup_view(request):
    error = None

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        User = get_user_model()

        if User.objects.filter(username=username).exists():
            error = "Username already exists"
        else:
            user = User.objects.create_user(
                username=username,
                password=password,
                user_type='student'
            )
            return redirect('login')

    return render(request, 'signup.html', {'error': error})


def create_course(request):
    if not request.user.is_authenticated or request.user.user_type != 'teacher':
        return redirect('login')

    if request.method == 'POST':
        title = request.POST['title']
        description = request.POST['description']

        Course.objects.create(
            title=title,
            description=description,
            teacher=request.user
        )

        return redirect('dashboard')

    return render(request, 'create_course.html')


def create_live_class(request):
    if not request.user.is_authenticated or request.user.user_type != 'teacher':
        return redirect('login')

    courses = Course.objects.filter(teacher=request.user)

    if request.method == 'POST':
        course_id = request.POST['course']
        title = request.POST['title']
        meet_link = request.POST['meet_link']
        whiteboard_link = request.POST['whiteboard_link']
        date = request.POST['date']

        LiveClass.objects.create(
            course_id=course_id,
            title=title,
            meet_link=meet_link,
            whiteboard_link=whiteboard_link,
            date=date
        )

        return redirect('dashboard')

    return render(request, 'create_live_class.html', {'courses': courses})


import razorpay
from django.conf import settings

def buy_course(request, course_id):
    course = Course.objects.get(id=course_id)

    client = razorpay.Client(auth=("rzp_test_SVTMhk0hvNVHGy", "STlXAEpa9EWmM4ddaxBO2sUF"))

    payment = client.order.create({
        "amount": course.price * 100,
        "currency": "INR",
        "payment_capture": "1",
        "notes": {
            "course_id": str(course.id),
            "user_id": str(request.user.id)
        }
    })

    return render(request, "payment.html", {
        "course": course,
        "payment": payment,
        "key": "rzp_test_SVTMhk0hvNVHGy"
    })

    

def payment_success(request, course_id):
    course = Course.objects.get(id=course_id)

    Enrollment.objects.get_or_create(
        student=request.user,
        course=course
    )

    return redirect('dashboard')


def course_detail(request, course_id):
    course = Course.objects.get(id=course_id)
    modules = Module.objects.filter(course=course)

    return render(request, 'course_detail.html', {
        'course': course,
        'modules': modules
    })


from django.shortcuts import get_object_or_404

def submit_assignment(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)

    if request.method == 'POST':
        file = request.FILES.get('file')

        if not file:
            return redirect('dashboard')
        
        Submission.objects.create(
            assignment=assignment,
            student=request.user,
            file=file
        )

        return redirect('dashboard')

    return render(request, 'submit_assignment.html', {'assignment': assignment})


def view_submissions(request, assignment_id):
    submissions = Submission.objects.filter(assignment_id=assignment_id)

    return render(request, 'view_submissions.html', {
        'submissions': submissions
    })


@csrf_exempt
def razorpay_webhook(request):
    data = json.loads(request.body)

    if data['event'] == 'payment.captured':
        payment = data['payload']['payment']['entity']
        course_id = payment['notes']['course_id']
        user_id = payment['notes']['user_id']

        user = User.objects.get(id=user_id)
        course = Course.objects.get(id=course_id)

        Enrollment.objects.get_or_create(
            student=user,
            course=course
        )

    return HttpResponse("OK")



from django.conf import settings

def ai_notes(request):
    notes = ""

    if request.method == "POST":
        topic = request.POST['topic']

        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": f"Explain {topic} simply"}]
            )

            notes = response.choices[0].message.content

        except Exception as e:
            notes = "Error generating notes"

    return render(request, 'ai_notes.html', {'notes': notes})


from django.contrib.auth import get_user_model
from django.http import HttpResponse

def create_admin(request):
    from django.contrib.auth import get_user_model
    from django.http import HttpResponse

    User = get_user_model()

    try:
        user, created = User.objects.get_or_create(username="admin1")

        user.set_password("Admin@123")
        user.user_type = "teacher"
        user.is_staff = True
        user.is_superuser = True
        user.save()

        return HttpResponse("Admin created")

    except Exception as e:
        return HttpResponse(f"Error: {str(e)}")
    

def attempt_quiz(request, quiz_id):
    quiz = Quiz.objects.get(id=quiz_id)
    questions = Question.objects.filter(quiz=quiz)

    if request.method == 'POST':
        score = 0

        for q in questions:
            selected = request.POST.get(str(q.id))

            if selected == q.correct_answer:
                score += 1

            StudentAnswer.objects.create(
                student=request.user,
                question=q,
                selected_answer=selected
            )

            from .models import QuizResult

    if request.method == 'POST':
        score = 0

        for q in questions:
            selected = request.POST.get(str(q.id))

            if selected == q.correct_answer:
                score += 1

            StudentAnswer.objects.create(
                student=request.user,
                question=q,
                selected_answer=selected
            )

            # SAVE RESULT
            QuizResult.objects.create(
                student=request.user,
                quiz=quiz,
                score=score,
                total=questions.count()
            )


        return HttpResponse(f"Your Score: {score}/{questions.count()}")

    return render(request, 'attempt_quiz.html', {
        'quiz': quiz,
        'questions': questions
    })


def generate_ai_notes(request, lesson_id):
    from django.http import HttpResponse
    from django.conf import settings
    from openai import OpenAI

    lesson = Lesson.objects.get(id=lesson_id)
    notes = ""

    if request.method == "POST":
        topic = request.POST.get("topic")

        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": f"Explain {topic} simply"
                }]
            )

            notes = response.choices[0].message.content

            # SAVE
            lesson.ai_notes = notes
            lesson.save()

        except Exception as e:
            return HttpResponse(f"ERROR: {str(e)}")

    return render(request, "ai_notes.html", {
        "lesson": lesson,
        "notes": notes
    })


def generate_ai_quiz(request, course_id):
    from django.shortcuts import get_object_or_404, redirect
    from django.http import HttpResponse
    from django.conf import settings
    from openai import OpenAI

    course = get_object_or_404(Course, id=course_id)

    if request.method == "POST":
        topic = request.POST.get("topic")

        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": f"Create 5 MCQs on {topic} in this format:\nQuestion|A|B|C|D|Correct"
                }]
            )

            content = response.choices[0].message.content

            # DEBUG (important)
            print("AI RESPONSE:", content)

            lines = content.strip().split("\n")

            # CREATE QUIZ
            quiz = Quiz.objects.create(
                course=course,
                title=f"AI Quiz - {topic}"
            )

            for line in lines:
                parts = line.split("|")

                if len(parts) == 6:
                    Question.objects.create(
                        quiz=quiz,
                        question=parts[0],
                        option1=parts[1],
                        option2=parts[2],
                        option3=parts[3],
                        option4=parts[4],
                        correct_answer=parts[5]
                    )

            return redirect(f"/quiz/{quiz.id}/")

        except Exception as e:
            return HttpResponse(f"ERROR: {str(e)}")

    return render(request, "ai_quiz.html", {"course": course})


def leaderboard(request):
    results = QuizResult.objects.all().order_by('-score')[:10]

    return render(request, 'leaderboard.html', {
        'results': results
    })