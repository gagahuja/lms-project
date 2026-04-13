from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('enroll/<int:course_id>/', views.enroll, name='enroll'),
    path('join/<int:class_id>/', views.join_class, name='join_class'),
    path('create-admin/', views.create_admin),
    path('signup/', views.signup_view, name='signup'),
    path('create-course/', views.create_course, name='create_course'),
    path('create-live-class/', views.create_live_class, name='create_live_class'),
    path('buy/<int:course_id>/', views.buy_course, name='buy_course'),
    path('payment-success/<int:course_id>/', views.payment_success),
    path('course/<int:course_id>/', views.course_detail, name='course_detail'),
    path('submit/<int:assignment_id>/', views.submit_assignment, name='submit_assignment'),
    path('submissions/<int:assignment_id>/', views.view_submissions),
    path('webhook/', views.razorpay_webhook),
    path('', views.home, name='home'),
    path('ai-notes/', views.ai_notes),
    path('quiz/<int:quiz_id>/', views.attempt_quiz),
    path('ai-notes/<int:lesson_id>/', views.generate_ai_notes),
    path('ai-quiz/<int:course_id>/', views.generate_ai_quiz),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('complete/<int:lesson_id>/', views.mark_complete),
    path('ai-insights/', views.ai_insights, name='ai_insights'),
    path('assignment/<int:assignment_id>/', views.view_assignment, name='view_assignment'),
    path('check-submissions/<int:assignment_id>/', views.check_submissions, name='check_submissions'),
    path('handout/<int:handout_id>/', views.view_handout, name='view_handout'),
    path('start-class/<int:class_id>/', views.start_class, name='start_class'),
    path('stop-class/<int:class_id>/', views.stop_class, name='stop_class'),
    path('join-class/<int:class_id>/', views.join_live_class, name='join_class'),
    path('attendance/<int:class_id>/', views.view_attendance),
    path('certificate/<int:course_id>/', views.generate_certificate),
    path('subscription/', views.subscription_page),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)