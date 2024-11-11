from django.core.exceptions import ObjectDoesNotExist
from .models import Quiz, Question, Answer, UserQuestionStatus
from django.db.models import Count, Exists, OuterRef
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import F
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
# Create your views here.


def dashboard(request):
    return render(request, 'dashboard.html')


def assignments(request):
    return render(request, 'assignments.html')


def resources(request):
    # Add any necessary context or data here
    resources_data = {
        # Example resources
        'articles': [
            {'title': 'Django OfficialDocumentation',
                'link': 'https://docs.djangoproject.com/en/stable/'},
            {'title': 'Django REST Framework',
                'link': 'https://www.django-rest-framework.org/'},
            {'title': 'Python Documentation', 'link': 'https://docs.python.org/3/'},
            {'title': 'Python ', 'link': 'https://docs.python.org/3/'},
            {'title': 'Python-the animal ', 'link': 'https://docs.python.org/3/'},
        ],
    }
    return render(request, 'resources/resources.html', resources_data)


def progress(request):
    return render(request, 'request.html')


@login_required
def quiz_list(request):
    """
    Display list of quizzes with their completion status and score for the current user.
    """
    quizzes = Quiz.objects.annotate(
        total_questions=Count('questions'),
        has_answers=Exists(
            UserQuestionStatus.objects.filter(
                user=request.user,
                old_answer__question__quiz=OuterRef('pk')
            )
        )
    ).all()

    for quiz in quizzes:
        if quiz.has_answers:
            answered_questions = UserQuestionStatus.objects.filter(
                user=request.user,
                old_answer__question__quiz=quiz
            ).count()
            quiz.completion = (answered_questions / quiz.total_questions) * 100

            # Calculate score for the quiz
            correct_answers = UserQuestionStatus.objects.filter(
                user=request.user,
                old_answer__question__quiz=quiz,
                old_answer__question__correct_answer_id=F('old_answer__id')
            ).count()
            quiz.score = (correct_answers / quiz.total_questions) * 100
        else:
            quiz.completion = 0
            quiz.score = 0

    return render(request, 'quizzes/quiz_list.html', {
        'quizzes': quizzes
    })


@login_required
def solve_quiz(request, quiz_id):
    """
    View for solving a specific quiz.
    """
    quiz = get_object_or_404(Quiz, pk=quiz_id)

    # Get the next unanswered question
    try:
        # Find questions that user hasn't answered yet
        answered_questions = UserQuestionStatus.objects.filter(
            user=request.user,
            old_answer__question__quiz=quiz
        ).values_list('old_answer__question_id', flat=True)

        next_question = Question.objects.filter(
            quiz=quiz
        ).exclude(
            id__in=answered_questions
        ).order_by('question_number').first()

        if next_question is None:
            # All questions are answered
            return render(request, 'quizzes/quiz_complete.html', {
                'quiz': quiz
            })

    except ObjectDoesNotExist:
        next_question = Question.objects.filter(
            quiz=quiz
        ).order_by('question_number').first()

    if request.method == 'POST':
        answer_id = request.POST.get('answer')
        if answer_id:
            answer = get_object_or_404(Answer, pk=answer_id)
            # Record user's answer
            UserQuestionStatus.objects.create(
                user=request.user,
                old_answer=answer
            )
            return redirect('solve_quiz', quiz_id=quiz_id)

    # Get all answers for the current question
    answers = Answer.objects.filter(question=next_question)

    return render(request, 'quizzes/solve_quiz.html', {
        'quiz': quiz,
        'question': next_question,
        'answers': answers
    })


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Redirect to your dashboard or home page
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'user/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'user/register.html', {'form': form})
