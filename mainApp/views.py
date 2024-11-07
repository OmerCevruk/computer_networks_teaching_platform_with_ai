from django.shortcuts import render

# Create your views here.

def dashboard(request):
    return render(request, 'dashboard.html')

def assignments(request):
    return render(request, 'assignments.html')

def quizzes(request):
    return render(request, 'quizzes.html')

def progress(request):
    return render(request, 'progress.html')

def resources(request):
    return render(request, 'resources.html')
