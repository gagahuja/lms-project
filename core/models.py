from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )

    user_type = models.CharField(
        max_length=10,
        choices=USER_TYPE_CHOICES,
        default='student'
    )
    last_seen = models.DateTimeField(null=True, blank=True)

class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    price = models.IntegerField(default=499)

    is_private = models.BooleanField(default=False)   # 👈 ADD THIS

    def __str__(self):
        return self.title
    

class Enrollment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.student.username} - {self.course.title}"
    

class LiveClass(models.Model):
    title = models.CharField(max_length=200)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date = models.DateTimeField()

    meeting_link = models.URLField(null=True, blank=True)

    is_live = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)

    whiteboard_link = models.URLField(null=True, blank=True)


class Attendance(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    live_class = models.ForeignKey(LiveClass, on_delete=models.CASCADE)
    attended = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.student.username} - {self.live_class.title}"
    

class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)

    def __str__(self):
        return self.title
    

class Lesson(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    video_url = models.URLField(blank=True, null=True)
    notes = models.FileField(upload_to='notes/', blank=True, null=True)
    ai_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title


class Assignment(models.Model):
    lesson = models.ForeignKey('Lesson', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='assignments/')
    due_date = models.DateField()

    def __str__(self):
        return self.title

class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    student = models.ForeignKey('User', on_delete=models.CASCADE)

    file = models.FileField(upload_to='submissions/')

    remarks = models.TextField(blank=True, null=True)
    checked_file = models.FileField(upload_to='checked/', blank=True, null=True)

    submitted_at = models.DateTimeField(auto_now_add=True)


class Progress(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)


class Quiz(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)

    def __str__(self):
        return self.title


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    question = models.CharField(max_length=300)
    option1 = models.CharField(max_length=200)
    option2 = models.CharField(max_length=200)
    option3 = models.CharField(max_length=200)
    option4 = models.CharField(max_length=200)
    correct_answer = models.CharField(max_length=200)

    def __str__(self):
        return self.question


class StudentAnswer(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_answer = models.CharField(max_length=200)


class QuizResult(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.IntegerField()
    total = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.quiz.title} ({self.score}/{self.total})"
    

class Points(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    points = models.IntegerField(default=0)


class Handout(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='handouts/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    

class Recording(models.Model):
    live_class = models.ForeignKey(
        LiveClass,
        on_delete=models.CASCADE,
        related_name='recordings'   # ✅ FIX
    )
    video = models.FileField(upload_to='recordings/')
    uploaded_at = models.DateTimeField(auto_now_add=True)


class Subscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plan = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(auto_now_add=True)


class CourseRequest(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student.username} → {self.course.title}"
    

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message
    

class Doubt(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    question = models.TextField()
    answer = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    text = models.TextField(null=True, blank=True)
    file = models.FileField(upload_to='chat_files/', null=True, blank=True)
    is_seen = models.BooleanField(default=False)  
    created_at = models.DateTimeField(auto_now_add=True)


class CallOffer(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    offer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class CallAnswer(models.Model):
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class IceCandidate(models.Model):
    candidate = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)