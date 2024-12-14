from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Exists, OuterRef, Q
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import F
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from asgiref.sync import sync_to_async
from django.template.loader import render_to_string
from .models import Quiz, Question, UserQuestionStatus, Course, CourseProgress
from .chat import OllamaChat
from datetime import timedelta
from typing import List, Dict
import asyncio


# Create your views here.

render_to_response = sync_to_async(render)
render_to_string_async = sync_to_async(render_to_string)


@login_required
async def ai_chat(request):
    # Initialize or get chat messages from session
    messages = request.session.get('ai_chat_messages', [])

    if request.method == 'POST':
        message = request.POST.get('message')
        if message:
            # Add user message to chat history
            messages.append({
                'content': message,
                'is_user': True
            })

            # Get AI response
            chat = OllamaChat()
            context = "You are a helpful AI teaching assistant specializing in computer networks. Provide clear, concise explanations."

            try:
                response = await chat.get_response(messages, context=context)

                # Add AI response to chat history
                messages.append({
                    'content': response,
                    'is_user': False
                })

                request.session['ai_chat_messages'] = messages
                request.session.modified = True

            except Exception as e:
                return JsonResponse({
                    'error': f'Error getting AI response: {str(e)}'
                }, status=500)

    # Render template asynchronously
    context = {
        'messages': messages,
        'user': request.user,  # Pass user explicitly
    }

    return await render_to_response(
        request,
        'ai_chat.html',
        context
    )


@login_required
def clear_chat(request):
    if 'ai_chat_messages' in request.session:
        request.session['ai_chat_messages'] = []
        request.session.modified = True
    return JsonResponse({'status': 'success'})


get_quiz = sync_to_async(get_object_or_404)


@sync_to_async
def get_user_answers(user, quiz):
    return list(UserQuestionStatus.objects.filter(
        user=user,
        question__quiz=quiz
    ).select_related('question'))


@sync_to_async
def process_answers(user_answers):
    processed = []
    for status in user_answers:
        question = status.question
        is_correct = status.selected_answer == question.correct_answer

        answers = {
            1: question.answer_1,
            2: question.answer_2,
            3: question.answer_3,
            4: question.answer_4
        }

        processed.append({
            'question_number': question.question_number,
            'question_text': question.question_text,
            'selected_answer': answers[status.selected_answer],
            'correct_answer': answers[question.correct_answer],
            'is_correct': is_correct
        })
    return processed


@login_required
async def quiz_chat(request, quiz_id):
    """
    Async view for quiz chat functionality using Ollama
    """
    try:
        # Get quiz using sync_to_async wrapper
        quiz = await get_quiz(Quiz, pk=quiz_id)

        if request.method == 'POST':
            message = request.POST.get('message')
            if not message:
                return JsonResponse({'error': 'Message is required'}, status=400)

            # Get and process user's answers
            user_answers = await get_user_answers(request.user, quiz)
            answers_context = await process_answers(user_answers)

            # Initialize chat if not in session
            if f'chat_messages_{quiz_id}' not in request.session:
                request.session[f'chat_messages_{quiz_id}'] = []

            # Add user message to session
            request.session[f'chat_messages_{quiz_id}'].append({
                'content': message,
                'is_user': True
            })

            # Prepare context for Ollama
            context = f"Quiz: {quiz.name}\n\nQuestion Review:\n"
            for answer in answers_context:
                context += f"\nQuestion {answer['question_number']
                                         }: {answer['question_text']}"
                context += f"\nYour answer: {answer['selected_answer']}"
                context += f"\nCorrect answer: {answer['correct_answer']}"
                context += f"\nStatus: {
                    'Correct' if answer['is_correct'] else 'Incorrect'}\n"

            # Get AI response
            chat = OllamaChat()
            try:
                response = await chat.get_response(
                    request.session[f'chat_messages_{quiz_id}'],
                    context=context
                )

                # Add AI response to session
                request.session[f'chat_messages_{quiz_id}'].append({
                    'content': response,
                    'is_user': False
                })

                request.session.modified = True

            except Exception as e:
                return JsonResponse({
                    'error': f'Error getting AI response: {str(e)}'
                }, status=500)

            return HttpResponseRedirect(reverse('quiz_chat', kwargs={'quiz_id': quiz_id}))

        # GET request handling
        user_answers = await get_user_answers(request.user, quiz)
        processed_answers = await process_answers(user_answers)

        # Render template using sync_to_async
        render_func = sync_to_async(render)
        return await render_func(request, 'quizzes/quiz_chat.html', {
            'quiz': quiz,
            'user_answers': processed_answers,
            'chat_messages': request.session.get(f'chat_messages_{quiz_id}', [])
        })

    except Exception as e:
        return JsonResponse({
            'error': f'Error processing request: {str(e)}'
        }, status=500)


@login_required
def dashboard(request):
    # Get user's quiz statistics
    user_stats = {}

    # Get all quizzes where user has at least one answer
    user_quiz_attempts = Quiz.objects.filter(
        questions__userquestionstatus__user=request.user
    ).distinct()

    # Count completed quizzes
    completed_quizzes = []
    for quiz in user_quiz_attempts:
        # Get all questions for this quiz
        total_questions = quiz.questions.count()
        # Get answered questions for this quiz
        answered_questions = UserQuestionStatus.objects.filter(
            user=request.user,
            question__quiz=quiz
        ).count()

        # If user has answered all questions, consider it completed
        if total_questions > 0 and answered_questions >= total_questions:
            completed_quizzes.append(quiz)

    user_stats['completed_quizzes'] = len(completed_quizzes)

    # Calculate average score for completed quizzes
    total_score = 0
    if completed_quizzes:
        for quiz in completed_quizzes:
            correct_answers = UserQuestionStatus.objects.filter(
                user=request.user,
                question__quiz=quiz,
                selected_answer=F('question__correct_answer')
            ).count()
            total_questions = quiz.questions.count()
            if total_questions > 0:
                quiz_score = (correct_answers / total_questions) * 100
                total_score += quiz_score

        user_stats['average_score'] = round(
            total_score / len(completed_quizzes))
    else:
        user_stats['average_score'] = 0

    # Count topics (based on unique quizzes attempted)
    user_stats['topics_covered'] = user_quiz_attempts.count()

    # Get featured topics
    featured_topics = [
        {
            'name': 'OSI Model',
            'description': 'Understand the seven layers of the OSI model and their functions in network communication.',
            'key_points': [
                'Physical Layer',
                'Data Link Layer',
                'Network Layer',
                'Transport Layer'
            ],
            'quiz_count': Quiz.objects.filter(name__icontains='OSI').count(),
            'completed_quizzes': len([q for q in completed_quizzes if 'OSI' in q.name])
        },
        {
            'name': 'TCP/IP Protocol Suite',
            'description': 'Master the fundamentals of TCP/IP and how it enables internet communication.',
            'key_points': [
                'IP Addressing',
                'Routing Protocols',
                'Transport Protocols',
                'Application Protocols'
            ],
            'quiz_count': Quiz.objects.filter(name__icontains='TCP').count(),
            'completed_quizzes': len([q for q in completed_quizzes if 'TCP' in q.name])
        },
        {
            'name': 'Network Security',
            'description': 'Learn about essential network security concepts and best practices.',
            'key_points': [
                'Firewalls',
                'Encryption',
                'Authentication',
                'Security Protocols'
            ],
            'quiz_count': Quiz.objects.filter(name__icontains='Security').count(),
            'completed_quizzes': len([q for q in completed_quizzes if 'Security' in q.name])
        }
    ]

    # Get latest updates
    latest_updates = [
        {
            'title': 'New Quiz Added: Network Protocols',
            'description': 'Test your knowledge of common networking protocols and their applications.',
            'date': timezone.now() - timedelta(days=1)
        },
        {
            'title': 'Updated Content: Cybersecurity Basics',
            'description': 'New materials added on network security fundamentals and best practices.',
            'date': timezone.now() - timedelta(days=3)
        },
        {
            'title': 'AI Assistant Improvement',
            'description': 'Enhanced capabilities for explaining complex networking concepts.',
            'date': timezone.now() - timedelta(days=5)
        }
    ]

    # Check if user needs welcome message
    user_stats['show_welcome'] = not UserQuestionStatus.objects.filter(
        user=request.user).exists()

    context = {
        'user_stats': user_stats,
        'featured_topics': featured_topics,
        'latest_updates': latest_updates
    }

    return render(request, 'dashboard.html', context)


def _calculate_topic_progress(user, topic_keyword):
    """Helper function to calculate user progress in a specific topic"""
    topic_quizzes = Quiz.objects.filter(name__icontains=topic_keyword)
    if not topic_quizzes.exists():
        return 0

    total_questions = Question.objects.filter(quiz__in=topic_quizzes).count()
    if total_questions == 0:
        return 0

    answered_questions = UserQuestionStatus.objects.filter(
        user=user,
        question__quiz__in=topic_quizzes
    ).count()

    return round((answered_questions / total_questions) * 100)


def assignments(request):
    return render(request, 'assignments.html')


@login_required
def resources(request):
    # Organize resources by categories
    resources_data = {
        'documentation': [
            {
                'title': 'Official Python Documentation',
                'description': 'Complete Python language reference and tutorials',
                'link': 'https://docs.python.org/3/',
                'type': 'Documentation'
            },
            {
                'title': 'RFC Documents',
                'description': 'Official networking protocol specifications',
                'link': 'https://www.ietf.org/standards/rfcs/',
                'type': 'Documentation'
            },
        ],
        'networking_basics': [
            {
                'title': 'Cisco Networking Basics',
                'description': 'Fundamental networking concepts and tutorials',
                'link': 'https://www.cisco.com/c/en/us/solutions/enterprise-networks/networking-basics.html',
                'type': 'Tutorial'
            },
            {
                'title': 'Computer Networks (Course)',
                'description': 'Comprehensive computer networks course materials',
                'link': 'https://gaia.cs.umass.edu/kurose_ross/lectures.php',
                'type': 'Course'
            },
        ],
        'security_resources': [
            {
                'title': 'NIST Cybersecurity Framework',
                'description': 'Guidelines for network security best practices',
                'link': 'https://www.nist.gov/cyberframework',
                'type': 'Framework'
            },
            {
                'title': 'OWASP Top 10',
                'description': 'Top 10 web application security risks',
                'link': 'https://owasp.org/www-project-top-ten/',
                'type': 'Security Guide'
            },
        ],
        'tools_software': [
            {
                'title': 'Wireshark',
                'description': 'Network protocol analyzer for network troubleshooting',
                'link': 'https://www.wireshark.org/',
                'type': 'Tool'
            },
            {
                'title': 'Network Mapper (Nmap)',
                'description': 'Network discovery and security scanning tool',
                'link': 'https://nmap.org/',
                'type': 'Tool'
            },
        ],
        'practice_labs': [
            {
                'title': 'Cisco Packet Tracer',
                'description': 'Network simulation and visualization tool',
                'link': 'https://www.netacad.com/courses/packet-tracer',
                'type': 'Lab'
            },
            {
                'title': 'GNS3',
                'description': 'Network software emulator',
                'link': 'https://www.gns3.com/',
                'type': 'Lab'
            },
        ]
    }

    return render(request, 'resources.html', {
        'resources_data': resources_data
    })


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
                question__quiz=OuterRef('pk')
            )
        )
    ).all()

    for quiz in quizzes:
        if quiz.has_answers:
            answered_questions = UserQuestionStatus.objects.filter(
                user=request.user,
                question__quiz=quiz
            ).count()
            quiz.completion = (answered_questions / quiz.total_questions) * 100

            # Calculate score for the quiz
            correct_answers = UserQuestionStatus.objects.filter(
                user=request.user,
                question__quiz=quiz
            ).filter(selected_answer=F('question__correct_answer')).count()

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

    # Check if user wants to retake the quiz
    if request.GET.get('retake'):
        # Delete all previous answers for this quiz
        UserQuestionStatus.objects.filter(
            user=request.user,
            question__quiz=quiz
        ).delete()

    # Get all questions for this quiz first
    quiz_questions = Question.objects.filter(
        quiz=quiz).order_by('question_number')

    # If no questions exist, return appropriate message
    if not quiz_questions.exists():
        return render(request, 'quizzes/solve_quiz.html', {
            'quiz': quiz,
            'no_questions': True
        })

    # Get answered questions
    answered_questions = UserQuestionStatus.objects.filter(
        user=request.user,
        question__quiz=quiz
    ).values_list('question_id', flat=True)

    # Get next unanswered question
    next_question = quiz_questions.exclude(
        id__in=answered_questions
    ).first()

    # If all questions are answered
    if next_question is None:
        return render(request, 'quizzes/quiz_complete.html', {
            'quiz': quiz,
            'show_retake': True
        })

    if request.method == 'POST':
        selected_answer = request.POST.get('answer')
        if selected_answer and selected_answer.isdigit():
            # Record user's answer
            UserQuestionStatus.objects.create(
                user=request.user,
                question=next_question,
                selected_answer=int(selected_answer)
            )
            return redirect('solve_quiz', quiz_id=quiz_id)

    # Prepare answers for the template
    answers = [
        {'number': 1, 'text': next_question.answer_1},
        {'number': 2, 'text': next_question.answer_2},
        {'number': 3, 'text': next_question.answer_3},
        {'number': 4, 'text': next_question.answer_4},
    ]

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


@login_required
def course_view(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)

    # Get or create course progress
    progress, _ = CourseProgress.objects.get_or_create(
        user=request.user,
        course=course
    )

    # Get chat messages from session
    chat_messages = request.session.get(f'chat_messages_{course.id}', [])

    context = {
        'course': course,
        'progress': progress,
        'chat_messages': chat_messages
    }

    template_name = f'courses/{course_slug}.html'
    return render(request, template_name, context)


# Helper functions with sync_to_async
get_course = sync_to_async(get_object_or_404)


@login_required
async def course_chat(request, course_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        # Get course using sync_to_async wrapper
        course = await get_course(Course, id=course_id)
        message = request.POST.get('message')

        if not message:
            return JsonResponse({'error': 'Message is required'}, status=400)

        # Initialize chat if not in session
        if f'chat_messages_{course_id}' not in request.session:
            request.session[f'chat_messages_{course_id}'] = []

        # Add user message to session
        request.session[f'chat_messages_{course_id}'].append({
            'content': message,
            'is_user': True
        })

        # Get AI response
        chat = OllamaChat()
        context = f"Course: {course.name}\nDescription: {course.description}"

        try:
            response = await chat.get_response(
                request.session[f'chat_messages_{course_id}'],
                context=context
            )

            # Add AI response to session
            request.session[f'chat_messages_{course_id}'].append({
                'content': response,
                'is_user': False
            })

            request.session.modified = True

            # Redirect back to the course page
            return HttpResponseRedirect(reverse('course_view', kwargs={'course_slug': course.slug}))

        except Exception as e:
            return JsonResponse({
                'error': str(e)
            }, status=500)

    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@login_required
def course_list(request):
    courses = Course.objects.all().order_by('name')

    # Get progress for each course
    for course in courses:
        progress, created = CourseProgress.objects.get_or_create(
            user=request.user,
            course=course,
            defaults={'completed': False}
        )
        course.user_progress = progress

    return render(request, 'courses/course_list.html', {
        'courses': courses
    })
