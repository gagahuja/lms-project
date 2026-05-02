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
from .models import Progress
from .models import Points
from .models import Handout
from django.utils import timezone
from datetime import timedelta
from reportlab.pdfgen import canvas
from .models import CourseRequest
from django.db.models import Count
from .models import Notification
from .models import Doubt
from .models import CallOffer
from .models import CallAnswer




def is_enrolled(user):
    
    return Enrollment.objects.filter(student=user).exists()


def login_view(request):
    error = None

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)


        if user is not None:
            login(request, user)

            from django.utils.timezone import now

            request.user.last_seen = now()
            request.user.save()

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
    from django.utils.timezone import now

    if not request.user.is_authenticated:
        request.user.last_seen = now()
        request.user.save()

        return redirect('login')
    
    recordings = []

    if getattr(request.user, 'user_type', None) == 'teacher':
        courses = Course.objects.filter(teacher=request.user)

        total_students = Enrollment.objects.filter(course__in=courses).count()
        total_classes = LiveClass.objects.filter(course__in=courses).count()

        total_revenue = Enrollment.objects.filter(
            course__in=courses
        ).count() * 500  # temporary logic

        total_assignments = Assignment.objects.filter(
            lesson__module__course__in=courses
        ).count()

        live_classes = LiveClass.objects.filter(course__in=courses)

        notifications = Notification.objects.filter(
            user=request.user
        ).order_by('-created_at')[:5]

        notification_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()

        return render(request, 'teacher_dashboard.html', {
            'courses': courses,
            'total_students': total_students,
            'total_classes': total_classes,
            'total_revenue': total_revenue,
            'total_assignments': total_assignments,
            'live_classes': live_classes,
            'notification_count': notification_count,
            'notifications': notifications,
        })
        
    else:
        enrolled = Enrollment.objects.filter(student=request.user)
        enrolled_courses = [e.course for e in enrolled]


        next_class = LiveClass.objects.filter(
            course__in=enrolled_courses,
            date__gte=timezone.now()
        ).order_by('date').first()

        live_classes = LiveClass.objects.filter(course__in=enrolled_courses)

        for cls in live_classes:
            now = timezone.now()

            cls.can_join = False
            cls.status = "Upcoming"

            # ⏳ Starting soon (5 min before)
            if cls.date - timedelta(minutes=5) <= now <= cls.date:
                cls.status = "Starting Soon"

            # 🔴 Live (use correct field)
            if cls.is_live:
                cls.status = "Live"

            # ✅ Completed
            if cls.is_completed or now > cls.date + timedelta(hours=2):
                cls.status = "Completed"

            # 🎯 Join condition
            if cls.is_live or (cls.date - timedelta(minutes=5) <= now <= cls.date + timedelta(hours=2)):
                cls.can_join = True

        
            

        # 📈 PROGRESS DATA
        progress_data = []

        for course in enrolled_courses:
            total_lessons = Lesson.objects.filter(module__course=course).count()

            completed_lessons = Progress.objects.filter(
                student=request.user,
                lesson__module__course=course,
                completed=True
            ).count()

            percent = 0
            if total_lessons > 0:
                percent = int((completed_lessons / total_lessons) * 100)

            # 🎓 CERTIFICATE CONDITION
            certificate_unlocked = percent >= 80

            if certificate_unlocked:
                Notification.objects.get_or_create(
                    user=request.user,
                    message=f"🎓 Certificate unlocked for {course.title}"
                )

            progress_data.append({
                'course': course,
                'percent': percent,
                'certificate': certificate_unlocked
            })

        # 📄 ASSIGNMENTS (based on enrolled courses)
        assignments = Assignment.objects.filter(
            lesson__module__course__in=enrolled_courses
        )

        assignment_data = []

        for assignment in assignments:
            submitted = Submission.objects.filter(
                assignment=assignment,
                student=request.user
            ).exists()

            assignment_data.append({
                'assignment': assignment,
                'submitted': submitted
            })

        # 🧠 QUIZ RESULTS
        quiz_results = QuizResult.objects.filter(student=request.user)

        from .models import Recording
        recordings = Recording.objects.filter(
                live_class__course__in=enrolled_courses
            )

        notifications = Notification.objects.filter(
            user=request.user
        ).order_by('-created_at')[:5]

        notification_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()

        return render(request, 'student_dashboard.html', {
            #'courses': courses,
            'enrolled_courses': enrolled_courses,
            'live_classes': live_classes,
            'progress_data': progress_data,
            'assignments': assignment_data,
            'quiz_results': quiz_results,
            'next_class': next_class,
            'recordings': recordings,
            'notification_count': notification_count,
            'notifications': notifications,
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


from django.shortcuts import render, get_object_or_404
from .models import LiveClass

def live_class(request, pk):
    try:
        room = LiveClass.objects.get(id=pk)
    except:
        return HttpResponse("Invalid class")

    return render(request, "agora_video.html", {
        "room_name": str(room.id)
    })

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


from django.shortcuts import render, redirect
from .models import LiveClass

def create_live_class(request):
    if request.method == "POST":
        LiveClass.objects.create(
            title=request.POST['title'],
            course_id=request.POST['course'],
            date=request.POST['date'],
            whiteboard_link=request.POST['whiteboard']
        )
        return redirect('dashboard')

    courses = Course.objects.filter(teacher=request.user)

    return render(request, "create_live_class.html", {"courses": courses})

import razorpay
from django.conf import settings

def buy_course(request, course_id):
    course = Course.objects.get(id=course_id)

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY, settings.RAZORPAY_SECRET)
    )

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


from django.shortcuts import get_object_or_404

def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # 🔒 CHECK ENROLLMENT
    is_enrolled = Enrollment.objects.filter(
        student=request.user,
        course=course
    ).exists()

    if not is_enrolled:
        return HttpResponse("❌ You must enroll to access this course")

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

        # ADD POINTS
        points_obj, created = Points.objects.get_or_create(student=request.user)
        points_obj.points += 10
        points_obj.save()

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

        # SAVE RESULT
        QuizResult.objects.create(
            student=request.user,
            quiz=quiz,
            score=score,
            total=questions.count()
        )

        # 🔔 NOTIFICATION (ADD THIS)
        Notification.objects.create(
            user=request.user,
            message=f"✅ Quiz submitted. Score: {score}/{questions.count()}"
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

    if not has_subscription(request.user):
        return HttpResponse("🔒 Upgrade to access AI Notes")

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

    # 🔒 LOCK AI QUIZ
    if not is_enrolled(request.user):
        return HttpResponse("🔒 Buy a course to access AI Quiz")
    

    # 🔒 LOCK
    if not has_subscription(request.user):
        return HttpResponse("🔒 Subscription required for AI Quiz")

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

    

from django.db.models import Sum
def leaderboard(request):
    from .models import User, QuizResult

    data = []

    students = User.objects.filter(user_type='student')

    for student in students:
        total_score = QuizResult.objects.filter(student=student).aggregate(
            total=Sum('score')
        )['total'] or 0

        data.append({
            'student': student,
            'score': total_score
        })

    # 🔥 SORT DESCENDING
    data = sorted(data, key=lambda x: x['score'], reverse=True)

    return render(request, 'leaderboard.html', {
        'data': data
    })


from django.shortcuts import redirect

def mark_complete(request, lesson_id):
    from .models import Lesson, Progress

    lesson = Lesson.objects.get(id=lesson_id)

    Progress.objects.update_or_create(
        student=request.user,
        lesson=lesson,
        defaults={'completed': True}
    )

    return redirect('dashboard')


def leaderboard(request):
    top_students = Points.objects.select_related('student').order_by('-points')[:10]

    return render(request, 'leaderboard.html', {
        'students': top_students
    })


def ai_insights(request):
    from django.db.models import Sum
    from .models import QuizResult
    from django.conf import settings

    # 🔒 SUBSCRIPTION LOCK
    if not has_subscription(request.user):
        return HttpResponse("🔒 Upgrade to Pro Plan to view AI Insights")
    
    user = request.user

    # 📊 TOTAL SCORE
    result = QuizResult.objects.filter(student=user).aggregate(total=Sum('score'))
    total_score = result['total'] or 0

    # 🧠 PERFORMANCE LEVEL
    if total_score < 5:
        level = "Weak"
    elif total_score < 15:
        level = "Average"
    else:
        level = "Strong"

    # 🤖 AI FEEDBACK
    feedback = ""

    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"A student has {level} performance with score {total_score}. Give short improvement advice."
            }]
        )

        feedback = response.choices[0].message.content

    except:
        feedback = "AI feedback not available"

    return render(request, "ai_insights.html", {
        "score": total_score,
        "level": level,
        "feedback": feedback
    })


from django.shortcuts import get_object_or_404

def view_assignment(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)

    if request.method == "POST":
        file = request.FILES.get("file")

        if file:
            Submission.objects.create(
                assignment=assignment,
                student=request.user,
                file=file
            )

        # 🔔 NOTIFY STUDENT
        Notification.objects.create(
            user=request.user,
            message=f"📄 You submitted assignment: {assignment.title}"
        )

        return redirect('dashboard')

    return render(request, "view_assignment.html", {
        "assignment": assignment
    })


def check_submissions(request, assignment_id):
    assignment = Assignment.objects.get(id=assignment_id)
    submissions = Submission.objects.filter(assignment=assignment)

    if request.method == "POST":
        submission_id = request.POST.get("submission_id")
        remarks = request.POST.get("remarks")
        checked_file = request.FILES.get("checked_file")

        submission = Submission.objects.get(id=submission_id)
        submission.remarks = remarks

        if checked_file:
            submission.checked_file = checked_file

        submission.save()

        return redirect('check_submissions', assignment_id=assignment.id)

    return render(request, 'check_submissions.html', {
        'assignment': assignment,
        'submissions': submissions
    })


def view_handout(request, handout_id):
    handout = Handout.objects.get(id=handout_id)

    return render(request, 'view_handout.html', {
        'handout': handout
    })


def start_class(request, class_id):
    cls = LiveClass.objects.get(id=class_id)
    cls.is_live = True
    cls.save()
    return redirect('dashboard')


def stop_class(request, class_id):
    cls = LiveClass.objects.get(id=class_id)
    cls.is_live = False
    cls.is_completed = True
    cls.save()
    return redirect('dashboard')


def join_live_class(request, class_id):
    if not request.user.is_authenticated:
        return redirect('login')

    cls = LiveClass.objects.get(id=class_id)

    # MARK ATTENDANCE
    Attendance.objects.get_or_create(
        student=request.user,
        live_class=cls
    )

    # REDIRECT TO MEET
    return redirect(cls.meeting_link)


def view_attendance(request, class_id):
    records = Attendance.objects.filter(live_class_id=class_id)

    return render(request, 'attendance.html', {
        'records': records
    })


def generate_certificate(request, course_id):
    from reportlab.pdfgen import canvas
    from django.http import HttpResponse
    from .models import Course
    import os
    from django.conf import settings
    import datetime

    course = Course.objects.get(id=course_id)
    user = request.user

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="certificate.pdf"'

    p = canvas.Canvas(response)

    width, height = 600, 800

    # 📁 IMAGE PATHS
    logo_path = os.path.join(settings.BASE_DIR, 'static/scoreskill_logo.png')
    bg_path = os.path.join(settings.BASE_DIR, 'static/certificate_bg.png')

    # 🖼️ BACKGROUND IMAGE (FIRST)
    if os.path.exists(bg_path):
        p.drawImage(bg_path, 0, 0, width=width, height=height)

    # 🟡 BORDER (optional if no bg)
    p.setLineWidth(4)
    p.rect(30, 30, width-60, height-60)

    # 🏷️ LOGO (TOP CENTER)
    if os.path.exists(logo_path):
        p.drawImage(logo_path, width/2 - 40, 720, width=80, height=80)

    # 🎓 TITLE
    p.setFont("Helvetica-Bold", 24)
    p.drawCentredString(width/2, 680, "Certificate of Completion")

    # 🧾 TEXT
    p.setFont("Helvetica", 14)
    p.drawCentredString(width/2, 640, "This is to certify that")

    # 👤 NAME
    p.setFont("Helvetica-Bold", 18)
    p.drawCentredString(width/2, 600, user.username)

    # 📘 TEXT
    p.setFont("Helvetica", 14)
    p.drawCentredString(width/2, 560, "has successfully completed")

    # 📚 COURSE
    p.setFont("Helvetica-Bold", 18)
    p.drawCentredString(width/2, 520, course.title)

    # 📅 DATE
    p.setFont("Helvetica", 12)
    p.drawCentredString(width/2, 480, f"Date: {datetime.date.today()}")

    # ✍️ SIGN
    p.drawString(80, 100, "Instructor Signature")

    p.save()

    return response


def has_subscription(user):
    from .models import Subscription
    return Subscription.objects.filter(user=user, is_active=True).exists()


def subscription_page(request):
    return render(request, "subscription.html")


def all_courses(request):
    courses = Course.objects.all()

    return render(request, 'all_courses.html', {
        'courses': courses
    })


def request_course(request, course_id):
    course = Course.objects.get(id=course_id)

    CourseRequest.objects.get_or_create(
        student=request.user,
        course=course
    )

    return HttpResponse("✅ Request sent to admin")


from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def admin_dashboard(request):
    from .models import User, Course, Enrollment

    total_users = User.objects.count()
    total_courses = Course.objects.count()
    total_enrollments = Enrollment.objects.count()

    # 💰 SIMPLE REVENUE CALCULATION
    total_revenue = sum([
        e.course.price for e in Enrollment.objects.select_related('course')
    ])

    return render(request, 'admin_dashboard.html', {
        'total_users': total_users,
        'total_courses': total_courses,
        'total_enrollments': total_enrollments,
        'total_revenue': total_revenue
    })


def buy_subscription(request):
    from .models import Subscription

    Subscription.objects.create(
        user=request.user,
        plan="Pro",
        is_active=True
    )

    return HttpResponse("✅ Subscription Activated")


from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def give_pro(request, user_id):
    from .models import Subscription, User

    user = User.objects.get(id=user_id)

    Subscription.objects.update_or_create(
        user=user,
        defaults={
            'plan': 'Pro',
            'is_active': True
        }
    )

    return HttpResponse(f"✅ Pro activated for {user.username}")


def notifications(request):
    notes = Notification.objects.filter(user=request.user).order_by('-created_at')

    # MARK ALL AS READ WHEN PAGE OPENED
    notes.update(is_read=True)

    return render(request, 'notifications.html', {
        'notifications': notes
    })



from django.http import JsonResponse

def get_notifications(request):
    notes = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]

    data = []

    for n in notes:
        data.append({
            "message": n.message,
            "time": str(n.created_at.strftime("%H:%M"))
        })

    count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    return JsonResponse({
        "notifications": data,
        "count": count
    })


def mark_notification_read(request, id):
    n = Notification.objects.get(id=id)
    n.is_read = True
    n.save()
    return redirect('/notifications/')


def doubts(request):
    doubts = Doubt.objects.filter(student=request.user)

    if request.method == "POST":
        question = request.POST.get("question")
        course_id = request.POST.get("course")

        Doubt.objects.create(
            student=request.user,
            course_id=course_id,
            question=question
        )

    return render(request, "doubts.html", {
        "doubts": doubts,
        "courses": Course.objects.all()
    })



def chat(request, user_id, course_id):
    from .models import Message

    other_user = User.objects.get(id=user_id)
    course = Course.objects.get(id=course_id)

    messages = Message.objects.filter(
        course=course
    ).filter(
        sender=request.user, receiver=other_user
    ) | Message.objects.filter(
        sender=other_user, receiver=request.user
    )

    messages = messages.order_by('created_at')
    
    if request.method == "POST":
        text = request.POST.get("text")
        file = request.FILES.get("file")

        if text or file:
            Message.objects.create(
                sender=request.user,
                receiver=other_user,
                course=course,
                text=text,
                file=file
            )

            # Notification
            from .models import Notification
            Notification.objects.create(
                user=other_user,
                message=f"💬 New message from {request.user.username}"
            )

        return redirect(request.path)
    
    messages.filter(receiver=request.user).update(is_seen=True)

    return render(request, "chat.html", {
        "messages": messages,
        "other_user": other_user,
        "course": course
    })


from django.http import JsonResponse

def typing(request):
    return JsonResponse({"status": "typing"})



import json
from django.http import JsonResponse

def save_offer(request):
    data = json.loads(request.body)

    CallOffer.objects.create(
        offer=data['offer']
    )

    return JsonResponse({"status": "saved"})


def get_offer(request):
    offer = CallOffer.objects.last()
    return JsonResponse({"offer": offer.offer})


def video_room(request):
    return render(request, "video_room.html")


def save_answer(request):
    import json
    data = json.loads(request.body)

    CallAnswer.objects.create(
        answer=data['answer']
    )

    return JsonResponse({"status": "saved"})


from .models import IceCandidate
def save_candidate(request):
    import json
    data = json.loads(request.body)

    IceCandidate.objects.create(
        candidate=data['candidate']
    )

    return JsonResponse({"status": "saved"})


def get_candidates(request):
    candidates = IceCandidate.objects.all().order_by('created_at')

    data = [c.candidate for c in candidates]

    return JsonResponse({"candidates": data})


def agora_video(request, class_id):
    from .models import LiveClass, Attendance

    cls = LiveClass.objects.get(id=class_id)

    # ✅ AUTO ATTENDANCE (only students)
    if request.user.user_type == "student":
        Attendance.objects.get_or_create(
            student=request.user,
            live_class=cls
        )

    return render(request, "agora_video.html", {
        "class_id": class_id,
        "class": cls
    })


def upload_recording(request, class_id):
    from .models import Recording

    if request.method == "POST":
        video = request.FILES.get("video")

        Recording.objects.create(
            live_class_id=class_id,
            video=video
        )

        return redirect("dashboard")

    return render(request, "upload_recording.html", {
        "class_id": class_id
    })


from django.http import JsonResponse
from .models import Message

def send_message(request, class_id):
    if request.method == "POST":
        text = request.POST.get("text")

        Message.objects.create(
            sender=request.user,
            live_class_id=class_id,
            text=text
        )

        return JsonResponse({"status": "sent"})
    

def get_messages(request, class_id):
    messages = Message.objects.filter(
        live_class_id=class_id
    ).order_by("timestamp")

    data = [
        {"user": m.sender.username, "text": m.text}
        for m in messages
    ]

    return JsonResponse({"messages": data})


import json
from django.http import JsonResponse

def ai_help(request):
    data = json.loads(request.body)
    question = data.get("question")

    # TEMP RESPONSE (you can connect OpenAI later)
    answer = "This is AI response to: " + question

    return JsonResponse({"answer": answer})


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage

@csrf_exempt
def upload_file(request):
    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]
        path = default_storage.save(f"chat_files/{file.name}", file)

        return JsonResponse({
            "url": default_storage.url(path),
            "name": file.name
        })

    return JsonResponse({"error": "Upload failed"})