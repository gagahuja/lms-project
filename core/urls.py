from django.urls import path
from . import views

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
]