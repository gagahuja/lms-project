from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from .views import upload_file
from django.contrib import messages
import os



urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('enroll/<int:course_id>/', views.enroll, name='enroll'),
    path('create-admin/', views.create_admin),
    path('signup/', views.signup_view, name='signup'),
    path('create-course/', views.create_course, name='create_course'),
    path('create-live-class/', views.create_live_class, name='create_live_class'),
    path('buy/<int:course_id>/', views.buy_course, name='buy_course'),
    path('payment-success/<int:course_id>/', views.payment_success),
    path('course/<int:course_id>/', views.course_detail, name='course_detail'),
    path("submit-assignment/<int:assignment_id>/",views.submit_assignment,name="submit_assignment"),
    path('submissions/<int:assignment_id>/',views.view_submissions,name='view_submissions'),
    path('webhook/', views.razorpay_webhook),
    path('home/', views.home, name='home'),
    path('ai-notes/', views.ai_notes),
    path('quiz/<int:quiz_id>/',views.attempt_quiz,name='attempt_quiz'),
    path('quiz-attempt/<int:result_id>/',views.quiz_attempt_review,name='quiz_attempt_review'),
    path('ai-notes/<int:lesson_id>/', views.generate_ai_notes),
    path("ai-quiz/<int:course_id>/",views.generate_ai_quiz,name="generate_ai_quiz"),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('complete-lesson/<int:lesson_id>/',views.mark_complete,name='complete_lesson'),
    path('ai-insights/', views.ai_insights, name='ai_insights'),
    path('assignment/<int:assignment_id>/', views.view_assignment, name='view_assignment'),
    path('check-submissions/<int:assignment_id>/', views.check_submissions, name='check_submissions'),
    path('handout/<int:handout_id>/', views.view_handout, name='view_handout'),
    path('start-class/<int:class_id>/', views.start_class, name='start_class'),
    path('stop-class/<int:class_id>/', views.stop_class, name='stop_class'),
    path('join-class/<int:class_id>/', views.join_live_class, name='join_class'),
    path('join-live-class/<int:class_id>/',views.join_live_class,name='join_live_class'),
    path('attendance/<int:class_id>/',views.view_attendance,name='attendance'),
    path('certificate/<int:course_id>/',views.generate_certificate,name='generate_certificate'),
    path('subscription/', views.subscription_page),
    path('courses/', views.all_courses, name='all_courses'),
    path('request-course/<int:course_id>/',views.request_course,name='request_course'),
    path('admin-dashboard/',views.admin_dashboard,name='admin_dashboard'),
    path('approve-course-request/<int:request_id>/',views.approve_course_request,name='approve_course_request'),
    path('buy-subscription/', views.buy_subscription),
    path('give-pro/<int:user_id>/', views.give_pro),
    path('api/notifications/', views.get_notifications),
    path('mark-read/<int:id>/', views.mark_notification_read),
    path('doubts/', views.doubts),
    path('notifications/', views.notifications, name='notifications'),
    path('chat/<int:user_id>/<int:course_id>/', views.chat),
    path('typing/', views.typing),
    path("live-class/<int:pk>/", views.live_class, name="live_class"),
    path('upload-recording/<int:class_id>/', views.upload_recording, name='upload_recording'),
    path('send-message/<int:class_id>/', views.send_message),
    path('get-messages/<int:class_id>/', views.get_messages),
    path('ai-help/', views.ai_help),
    path("upload/", views.upload_file),
    path('delete-recording/<int:recording_id>/',views.delete_recording,name='delete_recording'),
    path("gradebook/",views.gradebook,name="gradebook"),
    path("update-grade/<int:submission_id>/",views.update_grade,name="update_grade",),
    path("student-performance/",views.student_performance,name="student_performance",),
    path("student-report/<int:student_id>/",views.student_report,name="student_report",),
    path("teacher-analytics/",views.teacher_analytics,name="teacher_analytics",),
    path("student-analytics/",views.student_analytics,name="student_analytics",),
    path("lesson/<int:lesson_id>/",views.lesson_detail,name="lesson_detail"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)