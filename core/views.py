from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from .models import User
from .models import Course
from .models import Enrollment
from .models import StudentProfile
from .models import LiveClass
from .models import Attendance
from .models import Recording
from .models import Module
from .models import Assignment
from .models import Submission
from django.contrib.auth import get_user_model
from django.db.models import Count
import json
from django.views.decorators.csrf import csrf_exempt
from .models import Quiz, Question, StudentAnswer
from .models import Lesson
from .models import QuizResult, StudentAnswer
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
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.db.models import Avg, Max, Min, Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models.functions import TruncMonth
from collections import defaultdict
from .services.leaderboard_service import get_student_leaderboard
from core.services.xp_service import add_xp
from core.services.streak_service import update_streak
from core.services.achievement_service import award
from core.services.teacher_dashboard_service import get_basic_stats
from core.services.dashboard_stats import teacher_stats
from core.services.assignment_analytics_service import (
    get_assignment_statistics
)
from core.services.dashboard_service import (
    build_teacher_dashboard,
    build_student_dashboard,
)
from .services.quiz_analytics_service import get_quiz_analytics
from .services.ai_feedback_service import (
    generate_recommendations,
    generate_ai_feedback,
)
from .services.course_learning_service import (
    build_course_learning_context,
    get_lesson_learning_context,
)




def is_enrolled(user):
    
    return Enrollment.objects.filter(student=user).exists()


def login_view(request):

    error = None

    if request.method == 'POST':

        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)

            # ==========================================
            # UPDATE LAST SEEN
            # ==========================================

            from django.utils.timezone import now
            from datetime import timedelta

            request.user.last_seen = now()
            request.user.save()

            # ==========================================
            # UPDATE STUDENT STREAK
            # ==========================================

            if user.user_type == "student":

                profile, created = StudentProfile.objects.get_or_create(
                    student=user
                )

                today = now().date()

                # First login ever
                if profile.last_login_date is None:

                    profile.streak = 1

                # Already logged in today
                elif profile.last_login_date == today:

                    pass

                # Logged in yesterday
                elif profile.last_login_date == (
                    today - timedelta(days=1)
                ):

                    profile.streak += 1

                # Missed one or more days
                else:

                    profile.streak = 1

                # Update longest streak
                if profile.streak > profile.longest_streak:

                    profile.longest_streak = profile.streak

                # Save today's login date
                profile.last_login_date = today

                profile.save()

            return redirect('dashboard')

        else:

            error = "Invalid username or password"

    return render(
        request,
        'login.html',
        {
            'error': error
        }
    )

    


def logout_view(request):
    logout(request)
    return redirect('login')


def home(request):
    return render(request, 'home.html')


@login_required
def dashboard(request):

    if request.user.user_type == "teacher":

        context = build_teacher_dashboard(
            request.user
        )

        return render(
            request,
            "teacher_dashboard_v2.html",
            context
        )

    context = build_student_dashboard(
        request.user
    )

    return render(
        request,
        "student_dashboard.html",
        context
    )

        

@login_required
def teacher_analytics(request):

    if request.user.user_type != "teacher":
        return redirect("dashboard")

    courses = Course.objects.filter(
        teacher=request.user
    )

    print("Teacher:", request.user.username)
    print("Courses:", courses.count())
    print(list(courses.values("id", "title")))

    students = Enrollment.objects.filter(
        course__in=courses
    )

    assignments = Assignment.objects.filter(
        lesson__module__course__in=courses
    )

    submissions = Submission.objects.filter(
        assignment__lesson__module__course__in=courses
    )

    recordings = Recording.objects.filter(
        live_class__course__in=courses
    )

    live_classes = LiveClass.objects.filter(
        course__in=courses
    )

    monthly_enrollments = (
        students
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )

    monthly_submissions = (
        submissions
        .annotate(month=TruncMonth("submitted_at"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )

    context = {

        "total_courses": courses.count(),

        "total_students": students.count(),

        "total_assignments": assignments.count(),

        "total_submissions": submissions.count(),

        "pending_reviews": submissions.filter(
            status="submitted"
        ).count(),

        "average_marks":
            submissions.filter(
                marks__isnull=False
            ).aggregate(
                Avg("marks")
            )["marks__avg"] or 0,

        "total_recordings": recordings.count(),

        "total_live_classes": live_classes.count(),

    }

    context["enrollment_labels"] = [
        x["month"].strftime("%b %Y")
        for x in monthly_enrollments
        if x["month"]
    ]

    context["enrollment_data"] = [
        x["total"]
        for x in monthly_enrollments
        if x["month"]
    ]

    context["submission_labels"] = [
        x["month"].strftime("%b %Y")
        for x in monthly_submissions
        if x["month"]
    ]

    context["submission_data"] = [
        x["total"]
        for x in monthly_submissions
        if x["month"]
    ]

    context["enrollment_labels"]
    context["enrollment_data"]
    context["submission_labels"]
    context["submission_data"]

    return render(
        request,
        "teacher_analytics.html",
        context
    )
    


def enroll(request, course_id):
    if not request.user.is_authenticated:
        return redirect('login')

    course = Course.objects.get(id=course_id)

    Enrollment.objects.get_or_create(
        student=request.user,
        course=course
    )

    return redirect('dashboard')


from django.shortcuts import render
from django.http import HttpResponse

@login_required
def live_class(request, pk):

    try:
        room_id = str(pk)
    except Exception as e:
        return HttpResponse(f"Invalid room: {e}")

    return render(request, "agora_video.html", {
        "room_name": room_id,
        "user_name": request.user.username
    })



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
from django.utils.dateparse import parse_datetime

@login_required
def create_live_class(request):

    if request.user.user_type != "teacher":
        return redirect("dashboard")

    courses = Course.objects.filter(
        teacher=request.user
    )

    if request.method == "POST":

        title = request.POST.get("title")
        course_id = request.POST.get("course")
        date = request.POST.get("date")
        meeting_link = request.POST.get("meeting_link")
        whiteboard = request.POST.get("whiteboard")

        if not all([
            title,
            course_id,
            date,
            meeting_link
        ]):
            messages.error(
                request,
                "Please fill all required fields."
            )

            return redirect(
                "create_live_class"
            )

        parsed_date = parse_datetime(date)

        try:
            LiveClass.objects.create(
                title=title,
                course_id=course_id,
                date=parsed_date,
                meeting_link=meeting_link,
                whiteboard_link=whiteboard
            )

            messages.success(
                request,
                "Live class created successfully!"
            )

            return redirect(
                "dashboard"
            )

        except Exception as e:
            messages.error(
                request,
                str(e)
            )

    return render(
        request,
        "create_live_class.html",
        {
            "courses": courses
        }
    )

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

@login_required
def course_detail(request, course_id):

    course = get_object_or_404(
        Course,
        id=course_id
    )

    context = build_course_learning_context(
        request.user,
        course
    )

    return render(
        request,
        "course_detail.html",
        context
    )


@login_required
def lesson_detail(request, lesson_id):

    context = get_lesson_learning_context(
        request.user,
        lesson_id
    )

    if context is None:
        return HttpResponse(
            "Lesson not found.",
            status=404
        )

    if not context["is_enrolled"]:
        return HttpResponse(
            "You are not enrolled in this course.",
            status=403
        )

    return render(
        request,
        "lesson_detail.html",
        context
    )

from django.shortcuts import get_object_or_404

def submit_assignment(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)

    if request.method == 'POST':
        file = request.FILES.get('file')

        import os

        allowed_extensions = {
            ".pdf",
            ".doc",
            ".docx",
            ".ppt",
            ".pptx",
            ".zip",
        }

        extension = os.path.splitext(file.name)[1].lower()

        if extension not in allowed_extensions:
            messages.error(
                request,
                "Only PDF, DOC, DOCX, PPT, PPTX and ZIP files are allowed."
            )
            return redirect("submit_assignment", assignment_id=assignment.id)

        MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

        if file.size > MAX_FILE_SIZE:
            messages.error(
                request,
                "Maximum allowed file size is 20 MB."
            )
            return redirect("submit_assignment", assignment_id=assignment.id)

        if not file:
            return redirect('dashboard')

        if timezone.now().date() > assignment.due_date:
            messages.error(
                request,
                "Assignment submission deadline has passed."
            )
            return redirect("dashboard")
        
        submission, created = Submission.objects.update_or_create(
            assignment=assignment,
            student=request.user,
            defaults={
                "file": file
            }
        )
        # ADD POINTS
        if created:
            points, _ = Points.objects.get_or_create(
                student=request.user
            )

            points.points += 10
            points.save()

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

    questions = Question.objects.filter(
        quiz=quiz
    )

    if request.method == 'POST':

        score = 0
        answer_details = []

        # =====================================================
        # CALCULATE ANSWERS
        # =====================================================

        for q in questions:

            selected = request.POST.get(
                str(q.id)
            )

            is_correct = (
                selected == q.correct_answer
            )

            if is_correct:
                score += 1

            answer_details.append({
                'question': q,
                'selected_answer': selected,
                'correct_answer': q.correct_answer,
                'is_correct': is_correct,
            })

        # =====================================================
        # TOTAL + PERCENTAGE
        # =====================================================

        total = questions.count()

        percentage = (
            round((score / total) * 100)
            if total > 0
            else 0
        )

        # =====================================================
        # CREATE QUIZ RESULT FIRST
        # =====================================================

        quiz_result = QuizResult.objects.create(
            student=request.user,
            quiz=quiz,
            score=score,
            total=total
        )

        # =====================================================
        # SAVE STUDENT ANSWERS
        # LINK THEM TO THIS ATTEMPT
        # =====================================================

        for q in questions:

            selected = request.POST.get(
                str(q.id)
            )

            StudentAnswer.objects.create(
                student=request.user,
                question=q,
                quiz_result=quiz_result,
                selected_answer=selected
            )

        # =====================================================
        # NOTIFICATION
        # =====================================================

        Notification.objects.create(
            user=request.user,
            message=f"✅ Quiz submitted. Score: {score}/{total}"
        )

        # =====================================================
        # PERFORMANCE MESSAGE
        # =====================================================

        if percentage == 100:

            performance_message = (
                "Excellent! Perfect score! 🎉"
            )

        elif percentage >= 80:

            performance_message = (
                "Great work! You have done very well. 👍"
            )

        elif percentage >= 60:

            performance_message = (
                "Good effort! Keep practising to improve further. 👍"
            )

        elif percentage >= 40:

            performance_message = (
                "You are making progress. "
                "A little more practice will help. 📚"
            )

        else:

            performance_message = (
                "Keep practising. "
                "You can improve with more practice! 💪"
            )

        # =====================================================
        # RESULT PAGE
        # =====================================================

        return render(
            request,
            'quiz_result.html',
            {
                'quiz': quiz,

                'quiz_result': quiz_result,

                'score': score,
                'total': total,
                'percentage': percentage,

                'performance_message':
                    performance_message,

                'answer_details':
                    answer_details,
            }
        )

    # =========================================================
    # QUIZ PAGE
    # =========================================================

    return render(
        request,
        'attempt_quiz.html',
        {
            'quiz': quiz,
            'questions': questions
        }
    )



@login_required
def quiz_attempt_review(request, result_id):

    # =========================================================
    # GET THIS STUDENT'S QUIZ ATTEMPT
    # =========================================================

    quiz_result = get_object_or_404(
        QuizResult.objects.select_related("quiz"),
        id=result_id,
        student=request.user
    )


    # =========================================================
    # ATTEMPT NUMBER FOR THIS QUIZ
    # =========================================================

    attempt_number = QuizResult.objects.filter(
        student=request.user,
        quiz=quiz_result.quiz,
        created_at__lte=quiz_result.created_at
    ).count()

    # =========================================================
    # GET ONLY ANSWERS FROM THIS ATTEMPT
    # =========================================================

    answers = (
        StudentAnswer.objects
        .filter(
            student=request.user,
            quiz_result=quiz_result
        )
        .select_related("question")
        .order_by("question__id")
    )

    # =========================================================
    # PREPARE REVIEW DATA
    # =========================================================

    answer_details = []

    for answer in answers:

        question = answer.question

        is_correct = (
            answer.selected_answer
            == question.correct_answer
        )

        answer_details.append({
            "question": question,
            "selected_answer": answer.selected_answer,
            "correct_answer": question.correct_answer,
            "is_correct": is_correct,
        })

    # =========================================================
    # PERCENTAGE
    # =========================================================

    percentage = 0

    if quiz_result.total > 0:

        percentage = round(
            (quiz_result.score / quiz_result.total) * 100
        )

    # =========================================================
    # PERFORMANCE LEVEL
    # =========================================================

    if percentage >= 75:
        level = "Strong"

    elif percentage >= 50:
        level = "Average"

    else:
        level = "Needs Improvement"

    # =========================================================
    # RENDER
    # =========================================================

    return render(
        request,
        "quiz_attempt_review.html",
        {
            "quiz_result": quiz_result,
            "quiz": quiz_result.quiz,
            "answers": answer_details,
            "score": quiz_result.score,
            "total": quiz_result.total,
            "percentage": percentage,
            "level": level,
            "attempt_number": attempt_number,
        }
    )


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

    from django.http import HttpResponse
    from django.conf import settings
    from google import genai
    import re

    course = get_object_or_404(Course, id=course_id)

    # =========================================================
    # ACCESS CONTROL
    # =========================================================

    # TEACHER:
    # A teacher can generate AI quizzes for their own course.
    if request.user.user_type == "teacher":

        if course.teacher_id != request.user.id:
            return HttpResponse(
                "❌ You do not have permission to generate an AI Quiz for this course."
            )

    # STUDENT:
    # Student must be enrolled and subscribed.
    else:

        if not is_enrolled(request.user):
            return HttpResponse(
                "🔒 Buy a course to access AI Quiz"
            )

        if not has_subscription(request.user):
            return HttpResponse(
                "🔒 Subscription required for AI Quiz"
            )

    # =========================================================
    # MATHEMATICAL SYMBOL NORMALIZATION
    # =========================================================

    def normalize_math_text(text):

        if not text:
            return text

        text = text.strip()

        # Remove accidental markdown code fences
        text = text.replace("```text", "")
        text = text.replace("```", "")

        # -----------------------------------------------------
        # GEOMETRY SYMBOLS
        # -----------------------------------------------------

        # Triangle
        text = re.sub(
            r"\btriangle\s+([A-Za-z]{1,5})\b",
            r"△\1",
            text,
            flags=re.IGNORECASE
        )

        text = re.sub(
            r"\bdelta\s+([A-Za-z]{1,5})\b",
            r"△\1",
            text,
            flags=re.IGNORECASE
        )

        # Angle
        text = re.sub(
            r"\bangle\s+([A-Za-z]{2,5})\b",
            r"∠\1",
            text,
            flags=re.IGNORECASE
        )

        # Perpendicular
        text = re.sub(
            r"\bperpendicular\s+to\b",
            "⊥",
            text,
            flags=re.IGNORECASE
        )

        # Parallel
        text = re.sub(
            r"\bparallel\s+to\b",
            "∥",
            text,
            flags=re.IGNORECASE
        )

        # Congruent
        text = re.sub(
            r"\bcongruent\s+to\b",
            "≅",
            text,
            flags=re.IGNORECASE
        )

        # Similar
        text = re.sub(
            r"\bsimilar\s+to\b",
            "∼",
            text,
            flags=re.IGNORECASE
        )

        # -----------------------------------------------------
        # DEGREE SYMBOL
        # -----------------------------------------------------

        # 30 degrees → 30°
        text = re.sub(
            r"(\d+(?:\.\d+)?)\s+degrees?\b",
            r"\1°",
            text,
            flags=re.IGNORECASE
        )

        # 30 degree → 30°
        text = re.sub(
            r"(\d+(?:\.\d+)?)\s+degree\b",
            r"\1°",
            text,
            flags=re.IGNORECASE
        )

        # -----------------------------------------------------
        # COMMON MATHEMATICAL OPERATORS
        # -----------------------------------------------------

        text = re.sub(
            r"\bmultiplied\s+by\b",
            "×",
            text,
            flags=re.IGNORECASE
        )

        text = re.sub(
            r"\btimes\b",
            "×",
            text,
            flags=re.IGNORECASE
        )

        text = re.sub(
            r"\bdivided\s+by\b",
            "÷",
            text,
            flags=re.IGNORECASE
        )

        text = re.sub(
            r"\bplus\s+or\s+minus\b",
            "±",
            text,
            flags=re.IGNORECASE
        )

        text = re.sub(
            r"\bless\s+than\s+or\s+equal\s+to\b",
            "≤",
            text,
            flags=re.IGNORECASE
        )

        text = re.sub(
            r"\bgreater\s+than\s+or\s+equal\s+to\b",
            "≥",
            text,
            flags=re.IGNORECASE
        )

        text = re.sub(
            r"\bnot\s+equal\s+to\b",
            "≠",
            text,
            flags=re.IGNORECASE
        )

        text = re.sub(
            r"\bapproximately\s+equal\s+to\b",
            "≈",
            text,
            flags=re.IGNORECASE
        )

        # -----------------------------------------------------
        # COMMON GEOMETRY / NUMBER SYMBOLS
        # -----------------------------------------------------

        text = re.sub(
            r"\bpi\b",
            "π",
            text,
            flags=re.IGNORECASE
        )

        # Square root of 25 → √25
        text = re.sub(
            r"\bsquare\s+root\s+of\s+([0-9]+)\b",
            r"√\1",
            text,
            flags=re.IGNORECASE
        )

        return text.strip()

    # =========================================================
    # GENERATE AI QUIZ
    # =========================================================

    if request.method == "POST":

        topic = request.POST.get("topic", "").strip()

        if not topic:
            return HttpResponse(
                "❌ Please enter a topic for the AI Quiz."
            )

        try:

            # -------------------------------------------------
            # CONNECT TO GEMINI
            # -------------------------------------------------

            client = genai.Client(
                api_key=settings.GEMINI_API_KEY
            )

            # -------------------------------------------------
            # ASK GEMINI TO CREATE 5 MCQs
            # -------------------------------------------------

            prompt = f"""
Create exactly 5 multiple-choice questions for a school-level
quiz on the topic:

{topic}

Course:
{course.title}

Return ONLY the questions in this exact format:

Question|Option A|Option B|Option C|Option D|Correct Answer

IMPORTANT MATHEMATICAL FORMATTING RULES:

- Use standard mathematical symbols whenever a symbol exists.
- NEVER write "degree" or "degrees" when a degree symbol is appropriate.
  Use ° instead.
  Example: 60° NOT 60 degrees.

- NEVER write "delta ABC" or "triangle ABC".
  Use △ABC instead.

- NEVER write "angle ABC".
  Use ∠ABC instead.

- Use ⊥ for perpendicular.
- Use ∥ for parallel.
- Use ≅ for congruent.
- Use ∼ for similar.
- Use × for multiplication.
- Use ÷ for division.
- Use ≤ and ≥ where appropriate.
- Use ≠ for not equal.
- Use ≈ for approximately equal.
- Use π for pi.
- Use √ for square root where appropriate.

Examples of the required style:

△ABC has angles 30°, 60° and 90°.

If ∠ABC = 60°, find ∠ACB.

AB ⊥ CD.

AB ∥ CD.

△ABC ≅ △PQR.

- Use standard mathematical notation suitable for Class 9 and Class 10
  school mathematics.
- Do not replace mathematical symbols with their English names.
- Do not use the word "delta" to represent a triangle.
- Do not use the word "degree" to represent °.

GENERAL RULES:

- Exactly 5 questions.
- Each question must have exactly 4 options.
- The correct answer must be the exact text of one of the four options.
- Do not number the questions.
- Do not add explanations.
- Do not add markdown.
- Do not add headings.
- Do not use the | character inside a question or option.
- Keep each question and each option reasonably concise.
"""

            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt
            )

            content = response.text.strip()

            print("GEMINI RESPONSE:")
            print(content)

            # -------------------------------------------------
            # CREATE QUIZ
            # -------------------------------------------------

            quiz = Quiz.objects.create(
                course=course,
                title=f"AI Quiz - {topic}"
            )

            question_count = 0

            # -------------------------------------------------
            # READ GEMINI RESPONSE
            # -------------------------------------------------

            for line in content.splitlines():

                line = line.strip()

                if not line:
                    continue

                # Ignore accidental markdown fences
                if line.startswith("```"):
                    continue

                # -------------------------------------------------
                # SPLIT INTO 6 PARTS
                # -------------------------------------------------

                parts = [
                    part.strip()
                    for part in line.split("|", 5)
                ]

                if len(parts) != 6:
                    continue

                question_text = normalize_math_text(parts[0])
                option1 = normalize_math_text(parts[1])
                option2 = normalize_math_text(parts[2])
                option3 = normalize_math_text(parts[3])
                option4 = normalize_math_text(parts[4])
                correct_answer = normalize_math_text(parts[5])

                # -------------------------------------------------
                # CREATE QUESTION
                # -------------------------------------------------

                Question.objects.create(
                    quiz=quiz,
                    question=question_text,
                    option1=option1,
                    option2=option2,
                    option3=option3,
                    option4=option4,
                    correct_answer=correct_answer
                )

                question_count += 1

            # -------------------------------------------------
            # MAKE SURE QUESTIONS WERE CREATED
            # -------------------------------------------------

            if question_count == 0:

                quiz.delete()

                return HttpResponse(
                    "❌ Gemini returned an unexpected quiz format. "
                    "Please try again."
                )

            # -------------------------------------------------
            # SEND TEACHER TO QUIZ
            # -------------------------------------------------

            return redirect(
                f"/quiz/{quiz.id}/"
            )

        except Exception as e:

            print("GEMINI ERROR:", str(e))

            return HttpResponse(
                f"❌ Gemini error: {str(e)}"
            )

    # =========================================================
    # GET REQUEST
    # =========================================================

    return render(
        request,
        "ai_quiz.html",
        {
            "course": course
        }
    )



from django.shortcuts import redirect

@login_required
def mark_complete(request, lesson_id):

    from .models import Lesson, Progress, Enrollment
    from core.services.achievement_service import award

    lesson = get_object_or_404(
        Lesson,
        id=lesson_id
    )

    course = lesson.module.course

    # ---------------------------------------------------------
    # Make sure the student is enrolled in this course
    # ---------------------------------------------------------

    is_enrolled = Enrollment.objects.filter(
        student=request.user,
        course=course
    ).exists()

    if not is_enrolled:
        return HttpResponse(
            "You are not enrolled in this course.",
            status=403
        )

    # ---------------------------------------------------------
    # Check whether lesson was already completed
    # ---------------------------------------------------------

    progress = Progress.objects.filter(
        student=request.user,
        lesson=lesson
    ).first()

    already_completed = (
        progress is not None
        and progress.completed
    )

    # ---------------------------------------------------------
    # Mark lesson completed
    # ---------------------------------------------------------

    Progress.objects.update_or_create(
        student=request.user,
        lesson=lesson,
        defaults={
            "completed": True
        }
    )

    # ---------------------------------------------------------
    # FIRST LESSON COMPLETED ACHIEVEMENT
    # ---------------------------------------------------------

    if not already_completed:

        award(
            request.user,
            "First Lesson Completed"
        )

    # ---------------------------------------------------------
    # CHECK COURSE COMPLETION
    # ---------------------------------------------------------

    total_lessons = Lesson.objects.filter(
        module__course=course
    ).count()

    completed_lessons = Progress.objects.filter(
        student=request.user,
        lesson__module__course=course,
        completed=True
    ).count()

    course_completed = (
        total_lessons > 0
        and completed_lessons == total_lessons
    )

    # ---------------------------------------------------------
    # COURSE COMPLETED ACHIEVEMENT
    # ---------------------------------------------------------

    if course_completed:

        award(
            request.user,
            "Course Completed"
        )

    # ---------------------------------------------------------
    # Return to the same lesson
    # ---------------------------------------------------------

    return redirect(
        "lesson_detail",
        lesson_id=lesson.id
    )


def ai_insights(request):
    from django.db.models import Sum
    from django.http import HttpResponse
    from django.shortcuts import render
    from .models import QuizResult
    

    # =========================================================
    # SUBSCRIPTION LOCK
    # =========================================================

    user = request.user

    # =========================================================
    # ACCESS CONTROL
    # =========================================================

    # Teachers can use AI Insights for their students
    # without requiring a student subscription.
    if user.user_type != "teacher":

        if not has_subscription(user):
            return HttpResponse(
                "🔒 Upgrade to Pro Plan to view AI Insights"
            )

    # =========================================================
    # QUIZ ANALYTICS SERVICE
    # =========================================================

    analytics = get_quiz_analytics(user)
    

    # =========================================================
    # GET ANALYTICS FROM SERVICE
    # =========================================================

    total_score = analytics["score"]
    total_possible = analytics["total_possible"]
    percentage = analytics["percentage"]
    level = analytics["level"]

    quiz_history = analytics["quiz_history"]
    performance_trend = analytics["performance_trend"]

    topic_performance = analytics["topic_performance"]
    strongest_topic = analytics["strongest_topic"]
    weakest_topic = analytics["weakest_topic"]

    weaknesses = analytics["weaknesses"]
    focus_topics = analytics["focus_topics"]


    # =========================================================
    # PERSONALIZED RECOMMENDATIONS
    # =========================================================

    recommendations = generate_recommendations(
        weaknesses
    )


    # =========================================================
    # SUBSCRIPTION LOCK
    # =========================================================

    user = request.user

    # =========================================================
    # ACCESS CONTROL
    # =========================================================

    if user.user_type != "teacher":

        if not has_subscription(user):
            return HttpResponse(
                "🔒 Upgrade to Pro Plan to view AI Insights"
            )

    # =========================================================
    # QUIZ ANALYTICS SERVICE
    # =========================================================

    analytics = get_quiz_analytics(user)

    # =========================================================
    # GET ANALYTICS FROM SERVICE
    # =========================================================

    total_score = analytics["score"]
    total_possible = analytics["total_possible"]
    percentage = analytics["percentage"]
    level = analytics["level"]

    quiz_history = analytics["quiz_history"]
    performance_trend = analytics["performance_trend"]

    topic_performance = analytics["topic_performance"]
    strongest_topic = analytics["strongest_topic"]
    weakest_topic = analytics["weakest_topic"]

    weaknesses = analytics["weaknesses"]
    focus_topics = analytics["focus_topics"]

    # =========================================================
    # PERSONALIZED RECOMMENDATIONS
    # =========================================================

    recommendations = generate_recommendations(
        weaknesses
    )

    # =========================================================
    # AI FEEDBACK
    # =========================================================

    feedback = generate_ai_feedback(
        user,
        analytics
    )

    # =========================================================
    # DISPLAY INSIGHTS
    # =========================================================

    return render(
        request,
        "ai_insights.html",
        {
            "score": total_score,
            "total_possible": total_possible,
            "percentage": percentage,
            "level": level,
            "feedback": feedback,
            "quiz_history": quiz_history,
            "performance_trend": performance_trend,
            "topic_performance": topic_performance,
            "strongest_topic": strongest_topic,
            "weakest_topic": weakest_topic,
            "weaknesses": weaknesses,
            "focus_topics": focus_topics,
            "recommendations": recommendations,
        }
    )



from django.shortcuts import get_object_or_404

@login_required
def view_assignment(request, assignment_id):

    assignment = get_object_or_404(
        Assignment,
        id=assignment_id
    )

    from django.utils import timezone
    import os

    now = timezone.localtime()

    watermark_text = (
        f"This PDF belongs to:\n"
        f"{request.user.get_full_name() or request.user.username}\n"
        f"Viewed on:\n"
        f"{now.strftime('%d-%b-%Y %I:%M %p')}"
    )

    # -----------------------------------------------------
    # SUBMIT ASSIGNMENT
    # -----------------------------------------------------

    if request.method == "POST":

        file = request.FILES.get("file")

        if not file:

            messages.error(
                request,
                "Please select a file before submitting."
            )

            return redirect(
                "view_assignment",
                assignment_id=assignment.id
            )

        # -------------------------------------------------
        # FILE TYPE VALIDATION
        # -------------------------------------------------

        allowed_extensions = {
            ".pdf",
            ".doc",
            ".docx",
            ".ppt",
            ".pptx",
            ".zip",
        }

        extension = os.path.splitext(
            file.name
        )[1].lower()

        if extension not in allowed_extensions:

            messages.error(
                request,
                "Only PDF, DOC, DOCX, PPT, PPTX and ZIP files are allowed."
            )

            return redirect(
                "view_assignment",
                assignment_id=assignment.id
            )

        # -------------------------------------------------
        # FILE SIZE VALIDATION
        # -------------------------------------------------

        MAX_FILE_SIZE = 20 * 1024 * 1024

        if file.size > MAX_FILE_SIZE:

            messages.error(
                request,
                "Maximum allowed file size is 20 MB."
            )

            return redirect(
                "view_assignment",
                assignment_id=assignment.id
            )

        # -------------------------------------------------
        # DEADLINE CHECK
        # -------------------------------------------------

        if timezone.now().date() > assignment.due_date:

            messages.error(
                request,
                "Assignment submission deadline has passed."
            )

            return redirect(
                "view_assignment",
                assignment_id=assignment.id
            )

        # -------------------------------------------------
        # SAVE OR UPDATE SUBMISSION
        # -------------------------------------------------

        submission, created = (
            Submission.objects.update_or_create(
                assignment=assignment,
                student=request.user,
                defaults={
                    "file": file,
                    "status": "submitted",
                    "marks": None,
                    "remarks": "",
                }
            )
        )

        # -------------------------------------------------
        # STUDENT NOTIFICATION
        # -------------------------------------------------

        Notification.objects.create(
            user=request.user,
            message=(
                f"📄 You submitted assignment: "
                f"{assignment.title}"
            )
        )

        # -------------------------------------------------
        # POINTS FOR FIRST SUBMISSION
        # -------------------------------------------------

        if created:

            points, _ = Points.objects.get_or_create(
                student=request.user
            )

            points.points += 10

            points.save()

        messages.success(
            request,
            "Assignment submitted successfully."
        )

        return redirect(
            "view_assignment",
            assignment_id=assignment.id
        )

    # -----------------------------------------------------
    # CHECK EXISTING SUBMISSION
    # -----------------------------------------------------

    submission = (
        Submission.objects
        .filter(
            assignment=assignment,
            student=request.user
        )
        .first()
    )

    return render(
        request,
        "view_assignment.html",
        {
            "assignment": assignment,
            "watermark_text": watermark_text,
            "submission": submission,
        }
    )


from django.contrib.auth.decorators import login_required

@login_required
def check_submissions(request, assignment_id):

    if request.user.user_type != "teacher":
        return redirect("dashboard")

    assignment = get_object_or_404(
        Assignment,
        id=assignment_id,
        lesson__module__course__teacher=request.user
    )

    submissions = Submission.objects.filter(
        assignment=assignment
    )

    if request.method == "POST":

        submission_id = request.POST.get("submission_id")
        remarks = request.POST.get("remarks")
        marks = request.POST.get("marks")
        checked_file = request.FILES.get("checked_file")

        submission = get_object_or_404(
            Submission,
            id=submission_id,
            assignment=assignment
        )

        submission.remarks = remarks

        if marks:
            submission.marks = int(marks)

        if checked_file:
            submission.checked_file = checked_file

        submission.status = "checked"

        submission.save()

        Notification.objects.create(
            user=submission.student,
            message=(
                f"✅ Your assignment '{assignment.title}' "
                f"has been reviewed. "
                f"Marks: {submission.marks}. "
                f"Check your feedback and remarks."
            )
        )

        completed = Submission.objects.filter(
            student=submission.student,
            status="checked"
        ).count()

        if completed >= 10:

            award(
                submission.student,
                "Assignment Master"
            )

        from core.services.xp_service import add_xp

        add_xp(submission.student, 40)

        award(
            submission.student,
        "First Submission"
        )

        if submission.marks >= 90:
            add_xp(submission.student, 30)

        award(
            submission.student,
            "90+ Scorer"
        )

        add_xp(request.user, 20)

        return redirect(
            "check_submissions",
            assignment_id=assignment.id
        )

    return render(
        request,
        "check_submissions.html",
        {
            "assignment": assignment,
            "submissions": submissions,
        }
    )


def view_handout(request, handout_id):
    handout = Handout.objects.get(id=handout_id)

    return render(request, 'view_handout.html', {
        'handout': handout
    })


def start_class(request, class_id):
    cls = LiveClass.objects.get(id=class_id)

    cls.is_live = True
    cls.teacher_started = True

    cls.save()

    return redirect('dashboard')


@login_required
def stop_class(request, class_id):
    cls = LiveClass.objects.get(id=class_id)
    cls.is_live = False
    cls.is_completed = True
    cls.completed_at = timezone.now()
    cls.save()
    return redirect('dashboard')


def join_live_class(request, class_id):
    if not request.user.is_authenticated:
        return redirect('login')

    cls = LiveClass.objects.get(id=class_id)

    now = timezone.now()

    can_join = (
        cls.teacher_started
        or
        cls.date - timedelta(minutes=10)
        <= now
    )

    if not can_join:
        return HttpResponse(
            "Class will unlock 10 minutes before start time."
        )

    Attendance.objects.get_or_create(
        student=request.user,
        live_class=cls
    )

    return redirect(cls.meeting_link)


def view_attendance(request, class_id):
    records = Attendance.objects.filter(live_class_id=class_id)

    return render(request, 'attendance.html', {
        'records': records
    })


@login_required
def generate_certificate(request, course_id):

    from django.http import HttpResponse
    from .models import Course
    from django.conf import settings
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader
    import os
    import datetime

    # =========================================================
    # GET COURSE + STUDENT
    # =========================================================

    course = Course.objects.get(id=course_id)
    user = request.user

    # =========================================================
    # PDF RESPONSE
    # =========================================================

    response = HttpResponse(
        content_type="application/pdf"
    )

    response[
        "Content-Disposition"
    ] = (
        'attachment; filename="ScoreSkill_Certificate.pdf"'
    )

    # =========================================================
    # PAGE
    # =========================================================

    width, height = landscape(A4)

    p = canvas.Canvas(
        response,
        pagesize=(width, height)
    )

    # =========================================================
    # COLOURS
    # =========================================================

    dark = colors.HexColor("#172033")
    purple = colors.HexColor("#5B4BDB")
    purple_dark = colors.HexColor("#4338CA")
    gold = colors.HexColor("#C9A227")
    gold_light = colors.HexColor("#E8D28A")
    light_bg = colors.HexColor("#FAFAF7")
    grey = colors.HexColor("#64748B")
    white = colors.white

    # =========================================================
    # BACKGROUND
    # =========================================================

    p.setFillColor(light_bg)
    p.rect(
        0,
        0,
        width,
        height,
        fill=1,
        stroke=0
    )

    # =========================================================
    # OUTER GOLD BORDER
    # =========================================================

    p.setStrokeColor(gold)
    p.setLineWidth(3)

    p.rect(
        24,
        24,
        width - 48,
        height - 48,
        fill=0,
        stroke=1
    )

    # =========================================================
    # INNER BORDER
    # =========================================================

    p.setStrokeColor(purple)
    p.setLineWidth(1.2)

    p.rect(
        36,
        36,
        width - 72,
        height - 72,
        fill=0,
        stroke=1
    )

    # =========================================================
    # DECORATIVE TOP LINE
    # =========================================================

    center_x = width / 2

    p.setStrokeColor(gold)
    p.setLineWidth(2)

    p.line(
        center_x - 170,
        height - 80,
        center_x + 170,
        height - 80
    )

    # =========================================================
    # LOGO
    # =========================================================

    logo_path = os.path.join(
        settings.BASE_DIR,
        "static",
        "scoreskill_logo.png"
    )

    if os.path.exists(logo_path):

        logo = ImageReader(logo_path)

        logo_width = 72
        logo_height = 72

        p.drawImage(
            logo,
            center_x - (logo_width / 2),
            height - 155,
            width=logo_width,
            height=logo_height,
            preserveAspectRatio=True,
            mask="auto"
        )

    # =========================================================
    # BRAND NAME
    # =========================================================

    p.setFillColor(purple_dark)

    p.setFont(
        "Helvetica-Bold",
        12
    )

    p.drawCentredString(
        center_x,
        height - 175,
        "SCORESKILL"
    )

    p.setFillColor(grey)

    p.setFont(
        "Helvetica",
        8
    )

    p.drawCentredString(
        center_x,
        height - 188,
        "AI Powered Learning"
    )

    # =========================================================
    # MAIN TITLE
    # =========================================================

    p.setFillColor(dark)

    p.setFont(
        "Helvetica-Bold",
        28
    )

    p.drawCentredString(
        center_x,
        height - 235,
        "CERTIFICATE OF COMPLETION"
    )

    # =========================================================
    # SUBTITLE
    # =========================================================

    p.setFillColor(gold)

    p.setFont(
        "Helvetica-Bold",
        11
    )

    p.drawCentredString(
        center_x,
        height - 260,
        "This certificate is proudly presented to"
    )

    # =========================================================
    # STUDENT NAME
    # =========================================================

    student_name = (
        user.get_full_name().strip()
        if user.get_full_name()
        else user.username
    )

    p.setFillColor(dark)

    p.setFont(
        "Helvetica-Bold",
        25
    )

    p.drawCentredString(
        center_x,
        height - 305,
        student_name
    )

    # =========================================================
    # NAME UNDERLINE
    # =========================================================

    p.setStrokeColor(gold)
    p.setLineWidth(2)

    p.line(
        center_x - 150,
        height - 318,
        center_x + 150,
        height - 318
    )

    # =========================================================
    # COMPLETION TEXT
    # =========================================================

    p.setFillColor(grey)

    p.setFont(
        "Helvetica",
        12
    )

    p.drawCentredString(
        center_x,
        height - 355,
        "for successfully completing the course"
    )

    # =========================================================
    # COURSE NAME
    # =========================================================

    p.setFillColor(purple_dark)

    p.setFont(
        "Helvetica-Bold",
        21
    )

    p.drawCentredString(
        center_x,
        height - 392,
        course.title
    )

    # =========================================================
    # COURSE COMPLETION STATEMENT
    # =========================================================

    p.setFillColor(grey)

    p.setFont(
        "Helvetica",
        10
    )

    p.drawCentredString(
        center_x,
        height - 420,
        "This certificate recognizes the successful completion of the"
    )

    p.drawCentredString(
        center_x,
        height - 436,
        "learning requirements of the course on ScoreSkill."
    )

    # =========================================================
    # DATE + CERTIFICATE ID
    # =========================================================

    completion_date = datetime.date.today()

    certificate_id = (
        f"SS-{course.id:03d}-"
        f"{user.id:04d}-"
        f"{completion_date.strftime('%Y%m%d')}"
    )

    # LEFT INFORMATION

    left_x = 150

    p.setFillColor(grey)

    p.setFont(
        "Helvetica",
        8
    )

    p.drawString(
        left_x,
        108,
        "DATE OF COMPLETION"
    )

    p.setFillColor(dark)

    p.setFont(
        "Helvetica-Bold",
        10
    )

    p.drawString(
        left_x,
        91,
        completion_date.strftime("%d %B %Y")
    )

    # RIGHT INFORMATION

    right_x = width - 250

    p.setFillColor(grey)

    p.setFont(
        "Helvetica",
        8
    )

    p.drawString(
        right_x,
        108,
        "CERTIFICATE ID"
    )

    p.setFillColor(dark)

    p.setFont(
        "Helvetica-Bold",
        10
    )

    p.drawString(
        right_x,
        91,
        certificate_id
    )

    # =========================================================
    # INSTRUCTOR NAME
    # =========================================================

    instructor_name = (
        course.teacher.get_full_name().strip()
        if course.teacher.get_full_name()
        else course.teacher.username
    )

    # =========================================================
    # SIGNATURE SECTION
    # =========================================================

    signature_x = center_x

    p.setStrokeColor(dark)
    p.setLineWidth(1)

    p.line(
        signature_x - 85,
        110,
        signature_x + 85,
        110
    )

    p.setFillColor(dark)

    p.setFont(
        "Helvetica-Bold",
        9
    )

    p.drawCentredString(
        signature_x,
        94,
        instructor_name
    )

    p.setFillColor(grey)

    p.setFont(
        "Helvetica",
        8
    )

    p.drawCentredString(
        signature_x,
        80,
        "Instructor / Course Director"
    )

    # =========================================================
    # CERTIFICATION SEAL
    # =========================================================

    seal_x = width - 115
    seal_y = height - 125

    p.setStrokeColor(gold)
    p.setLineWidth(2)

    p.circle(
        seal_x,
        seal_y,
        32,
        fill=0,
        stroke=1
    )

    p.setStrokeColor(purple)
    p.setLineWidth(1)

    p.circle(
        seal_x,
        seal_y,
        25,
        fill=0,
        stroke=1
    )

    p.setFillColor(purple_dark)

    p.setFont(
        "Helvetica-Bold",
        8
    )

    p.drawCentredString(
        seal_x,
        seal_y + 5,
        "SCORESKILL"
    )

    p.setFont(
        "Helvetica-Bold",
        7
    )

    p.drawCentredString(
        seal_x,
        seal_y - 6,
        "CERTIFIED"
    )

    # =========================================================
    # FOOTER
    # =========================================================

    p.setFillColor(purple_dark)

    p.setFont(
        "Helvetica-Bold",
        8
    )

    p.drawCentredString(
        center_x,
        55,
        "ScoreSkill - Smart Learning Platform"
    )

    # =========================================================
    # SAVE
    # =========================================================

    p.showPage()
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


from django.shortcuts import get_object_or_404

@login_required
def upload_recording(request, class_id):
    live_class = get_object_or_404(LiveClass, id=class_id)

    # Only the teacher who owns the course can upload
    if live_class.course.teacher != request.user:
        return redirect("dashboard")

    recording = Recording.objects.filter(
        live_class=live_class
    ).first()

    if request.method == "POST":
        video = request.FILES.get("video")

        if video:
            try:
                recording, created = Recording.objects.update_or_create(
                    live_class=live_class,
                    defaults={
                        "video": video
                    }
                )

                messages.success(
                    request,
                    "Recording uploaded successfully."
                )

                return redirect("dashboard")

            except Exception as e:
                print("RECORDING ERROR:", str(e))
                return HttpResponse(f"ERROR: {str(e)}")

    return render(
        request,
        "upload_recording.html",
        {
            "class_obj": live_class,
            "recording": recording,
        }
    )


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



from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST

@require_POST
@login_required
def delete_recording(request, recording_id):
    recording = get_object_or_404(Recording, id=recording_id)

    # Only the course teacher can delete
    if recording.live_class.course.teacher != request.user:
        messages.error(request, "You are not authorized to delete this recording.")
        return redirect("dashboard")

    # Delete the video file from storage
    try:
        if recording.video:
            recording.video.delete(save=False)

        recording.delete()

        messages.success(
            request,
            "Recording deleted successfully."
        )

    except Exception as e:
        messages.error(
            request,
            f"Unable to delete recording: {e}"
        )

    return redirect("dashboard")

    messages.success(request, "Recording deleted successfully.")

    return redirect("dashboard")


from django.contrib.auth.decorators import login_required

@login_required
def gradebook(request):

    if request.user.user_type != "teacher":
        return redirect("dashboard")

    submissions = Submission.objects.filter(
        assignment__lesson__module__course__teacher=request.user
    ).select_related(
        "student",
        "assignment",
        "assignment__lesson__module__course"
    )

    total = submissions.count()

    checked = submissions.filter(
        status="checked"
    ).count()

    checked_percent = 0

    if total:
        checked_percent = round(
            checked * 100 / total
        )

    # -----------------------
    # FILTERS
    # -----------------------

    student = request.GET.get("student")
    course = request.GET.get("course")
    assignment = request.GET.get("assignment")
    status = request.GET.get("status")

    if student:
        submissions = submissions.filter(
            student__username__icontains=student
        )

    if course:
        submissions = submissions.filter(
            assignment__lesson__module__course_id=course
        )

    if assignment:
        submissions = submissions.filter(
            assignment_id=assignment
        )

    if status:
        submissions = submissions.filter(
            status=status
        )

    stats = submissions.aggregate(
        average=Avg("marks"),
        highest=Max("marks"),
        lowest=Min("marks"),
        total=Count("id"),
    )

    pending_reviews = submissions.filter(
        status="submitted"
    ).count()

    courses = Course.objects.filter(
        teacher=request.user
    )

    assignments = Assignment.objects.filter(
        lesson__module__course__teacher=request.user
    )

    return render(
        request,
        "gradebook.html",
        {
            "submissions": submissions,
            "courses": courses,
            "assignments": assignments,
            "stats": stats,
            "pending_reviews": pending_reviews,
            "checked_percent": checked_percent,
        },
    )


from django.views.decorators.http import require_POST

@require_POST
@login_required
def update_grade(request, submission_id):

    if request.user.user_type != "teacher":
        return redirect("dashboard")

    submission = get_object_or_404(
        Submission,
        id=submission_id,
        assignment__lesson__module__course__teacher=request.user
    )

    marks = request.POST.get("marks")
    remarks = request.POST.get("remarks")

    if marks:
        submission.marks = int(marks)

    submission.remarks = remarks
    submission.status = "checked"
    submission.save()

    return redirect("gradebook")



from django.contrib.auth.decorators import login_required

@login_required
def student_performance(request):

    if request.user.user_type != "teacher":
        return redirect("dashboard")

    students = (
        User.objects.filter(
            enrollment__course__teacher=request.user
        )
        .distinct()
    )

    student_stats = []

    for student in students:

        # Courses of this teacher in which the student is enrolled
        enrollments = Enrollment.objects.filter(
            student=student,
            course__teacher=request.user
        )

        courses = [e.course for e in enrollments]

        # ---------- Assignments ----------
        assignments = Assignment.objects.filter(
            lesson__module__course__in=courses
        )

        total_assignments = assignments.count()

        submissions = Submission.objects.filter(
            assignment__in=assignments,
            student=student
        )

        submitted = submissions.count()

        pending = total_assignments - submitted

        # ---------- Marks ----------
        average_marks = submissions.aggregate(
            Avg("marks")
        )["marks__avg"] or 0

        highest_marks = submissions.aggregate(
            Max("marks")
        )["marks__max"] or 0

        lowest_marks = submissions.aggregate(
            Min("marks")
        )["marks__min"] or 0

        # ---------- Lessons ----------
        total_lessons = Lesson.objects.filter(
            module__course__in=courses
        ).count()

        completed_lessons = Progress.objects.filter(
            student=student,
            lesson__module__course__in=courses,
            completed=True
        ).count()

        lesson_progress = 0

        if total_lessons:
            lesson_progress = round(
                completed_lessons * 100 / total_lessons
            )

        # ---------- Attendance ----------
        total_live = LiveClass.objects.filter(
            course__in=courses
        ).count()

        attended = Attendance.objects.filter(
            student=student,
            live_class__course__in=courses
        ).count()

        attendance = 0

        if total_live:
            attendance = round(
                attended * 100 / total_live
            )

        # ---------- Quiz ----------
        quiz_average = QuizResult.objects.filter(
            student=student,
            quiz__course__in=courses
        ).aggregate(
            Avg("score")
        )["score__avg"] or 0

        student_stats.append({

            "student": student,

            "submitted": submitted,

            "pending": pending,

            "average": round(average_marks, 1),

            "highest": highest_marks,

            "lowest": lowest_marks,

            "progress": lesson_progress,

            "attendance": attendance,

            "quiz_average": round(quiz_average, 1),

        })

    return render(
        request,
        "student_performance.html",
        {
            "student_stats": student_stats,
        }
    )



@login_required
def student_report(request, student_id):

    if request.user.user_type != "teacher":
        return redirect("dashboard")

    student = get_object_or_404(User, id=student_id)

    courses = Course.objects.filter(
        teacher=request.user,
        enrollment__student=student
    ).distinct()

    assignments = Assignment.objects.filter(
        lesson__module__course__in=courses
    )

    submissions = Submission.objects.filter(
        student=student,
        assignment__in=assignments
    )

    total_assignments = assignments.count()

    submitted = submissions.count()

    pending = max(total_assignments - submitted, 0)

    average_marks = submissions.aggregate(
        Avg("marks")
    )["marks__avg"] or 0

    highest_marks = submissions.order_by("-marks").first()

    lowest_marks = submissions.exclude(
        marks__isnull=True
    ).order_by("marks").first()

    total_lessons = Lesson.objects.filter(
        module__course__in=courses
    ).count()

    completed_lessons = Progress.objects.filter(
        student=student,
        lesson__module__course__in=courses,
        completed=True
    ).count()

    progress = 0
    remaining_progress = 100

    if total_lessons:
        progress = round(
            completed_lessons * 100 / total_lessons
        )

        remaining_progress = max(0, 100 - progress)

    total_live = LiveClass.objects.filter(
        course__in=courses
    ).count()

    attended = Attendance.objects.filter(
        student=student,
        live_class__course__in=courses
    ).count()

    attendance = 0

    if total_live:
        attendance = round(
            attended * 100 / total_live
        )

    quiz_average = QuizResult.objects.filter(
        student=student,
        quiz__course__in=courses
    ).aggregate(
        Avg("score")
    )["score__avg"] or 0

    return render(
        request,
        "student_report.html",
        {
            "student": student,
            "courses": courses,
            "submissions": submissions,
            "attendance": attendance,
            "progress": progress,
            "remaining_progress": remaining_progress,
            "submitted": submitted,
            "pending": pending,
            "average_marks": round(average_marks, 1),
            "highest_marks": highest_marks,
            "lowest_marks": lowest_marks,
            "quiz_average": round(quiz_average, 1),
            "submitted": submitted,
            "pending": pending,
        },
    )


@login_required
def student_analytics(request):

    if request.user.user_type != "student":
        return redirect("dashboard")

    enrollments = Enrollment.objects.filter(
        student=request.user
    )

    courses = Course.objects.filter(
        id__in=enrollments.values_list("course_id", flat=True)
    )

    assignments = Submission.objects.filter(
        student=request.user
    )

    checked = assignments.filter(
        marks__isnull=False
    )

    quizzes = QuizResult.objects.filter(
        student=request.user
    )

    attendance = Attendance.objects.filter(
        student=request.user
    )

    average_marks = (
        checked.aggregate(
            Avg("marks")
        )["marks__avg"] or 0
    )

    average_quiz = (
        quizzes.aggregate(
            Avg("score")
        )["score__avg"] or 0
    )

    attendance_percent = 0

    total_live_classes = LiveClass.objects.filter(
        course__in=courses
    ).count()

    attended_classes = attendance.count()

    if total_live_classes > 0:

        attendance_percent = round(
            attended_classes * 100 / total_live_classes
        )

    progress = 0

    if assignments.exists():

        total_assignments = assignments.count()

        completed_assignments = assignments.filter(
            status="checked"
        ).count()

        if total_assignments:

            progress = round(
                completed_assignments * 100 /
                total_assignments
            )

    # Assignment Chart

    checked_count = assignments.filter(
        status="checked"
    ).count()

    pending_count = assignments.filter(
        status="submitted"
    ).count()

    # Attendance Chart


    missed_classes = max(
        total_live_classes - attended_classes,
        0
    )

    monthly_marks = (
        checked
        .annotate(month=TruncMonth("submitted_at"))
        .values("month")
        .annotate(avg_marks=Avg("marks"))
        .order_by("month")
    )

    # ==========================
    # AI Learning Insights
    # ==========================

    ai_insights = []

    # Attendance
    if attendance_percent >= 90:
        ai_insights.append(
            "🎉 Excellent attendance! Keep it up."
        )
    elif attendance_percent >= 75:
        ai_insights.append(
            "🙂 Good attendance, but there is room for improvement."
        )
    else:
        ai_insights.append(
            "⚠ Your attendance is low. Attend more live classes regularly."
        )


    # Assignment Completion
    if progress == 100:
        ai_insights.append(
            "✅ Great job! You have completed all your assignments."
        )
    elif progress >= 70:
        ai_insights.append(
            "📚 You are doing well. Finish the remaining assignments."
        )
    else:
        ai_insights.append(
            "❗ Complete more assignments to improve your learning."
        )


    # Marks
    if average_marks >= 80:
        ai_insights.append(
            "🏆 Excellent academic performance."
        )
    elif average_marks >= 60:
        ai_insights.append(
            "📈 Good performance. Keep practising."
        )
    else:
        ai_insights.append(
            "📖 Spend more time revising weak topics."
        )


    # Quiz
    if quizzes.count() == 0:
        ai_insights.append(
            "📝 You haven't attempted any quizzes yet."
        )
    else:
        ai_insights.append(
            "🎯 Continue taking quizzes to improve."
        )


    context = {

        "course_count": courses.count(),

        "assignment_count": assignments.count(),

        "quiz_count": quizzes.count(),

        "average_marks": round(average_marks,1),

        "average_quiz": round(average_quiz,1),

        "attendance_percent": attendance_percent,

        "progress": progress,

        "assignment_chart_json": json.dumps([
            checked_count,
            pending_count
        ]),

        "attendance_chart_json": json.dumps([
            attended_classes,
            missed_classes
        ]),

        "ai_insights": ai_insights,

        "marks_labels_json": json.dumps(
            [x["month"].strftime("%b %Y") for x in monthly_marks]
        ),

        "marks_data_json": json.dumps(
            [float(x["avg_marks"]) for x in monthly_marks]
        ),


    }

    return render(
        request,
        "student_analytics.html",
        context
    )


@login_required
def leaderboard(request):

    leaderboard = get_student_leaderboard()

    user_rank = None

    for row in leaderboard:

        if row["student"] == request.user:

            user_rank = row["rank"]

            break

    return render(

        request,

        "leaderboard.html",

        {

            "leaderboard": leaderboard,

            "user_rank": user_rank,

        }

    )