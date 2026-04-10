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


class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    price = models.IntegerField(default=0)

    def __str__(self):
        return self.title
    

class Enrollment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.student.username} - {self.course.title}"
    

class LiveClass(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    meet_link = models.URLField()
    whiteboard_link = models.URLField(blank=True, null=True)
    date = models.DateTimeField()

    def __str__(self):
        return self.title


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