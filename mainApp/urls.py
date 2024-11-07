from django.contrib import admin
from django.urls import path, include
from . import views  # Import the view function for the home page

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('assignments/', views.assignments, name='assignments'),
    path('quizzes/', views.quizzes, name='quizzes'),
    path('progress/', views.progress, name='progress'),
    path('resources/', views.resources, name='resources'),
]
