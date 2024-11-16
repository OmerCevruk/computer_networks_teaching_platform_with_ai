from django.contrib import admin
from django.urls import path, include
from . import views  # Import the view function for the home page

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('assignments/', views.assignments, name='assignments'),
    path('quizzes/', views.quiz_list, name='quizzes'),
    path('progress/', views.progress, name='progress'),
    path('resources/', views.resources, name='resources'),
    path('quiz/<int:quiz_id>/solve/', views.solve_quiz, name='solve_quiz'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('quiz/<int:quiz_id>/chat/', views.quiz_chat, name='quiz_chat'),
]
