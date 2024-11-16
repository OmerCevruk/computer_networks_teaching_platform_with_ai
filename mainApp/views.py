from django.core.exceptions import ObjectDoesNotExist
from .models import Quiz, Question, UserQuestionStatus
from django.db.models import Count, Exists, OuterRef
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import F
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
import torch
from transformers import GPT2LMHeadModel, GPT2Tokenizer

tokenizer = GPT2Tokenizer.from_pretrained('gpt2')
model = GPT2LMHeadModel.from_pretrained('gpt2')

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


@login_required
def quiz_chat(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)

    # Get user's answers for this quiz
    user_answers_query = UserQuestionStatus.objects.filter(
        user=request.user,
        question__quiz=quiz
    ).select_related('question')

    # Process answers for context
    user_answers = []
    for status in user_answers_query:
        question = status.question
        is_correct = status.selected_answer == question.correct_answer

        answers = {
            1: question.answer_1,
            2: question.answer_2,
            3: question.answer_3,
            4: question.answer_4
        }

        user_answers.append({
            'question_number': question.question_number,
            'question_text': question.question_text,
            'selected_answer': answers[status.selected_answer],
            'correct_answer': answers[question.correct_answer],
            'is_correct': is_correct
        })

    # Initialize or get chat messages from session
    if f'chat_messages_{quiz_id}' not in request.session:
        request.session[f'chat_messages_{quiz_id}'] = []

    if request.method == 'POST':
        user_message = request.POST.get('message')
        if user_message:
            # Add user message to chat
            request.session[f'chat_messages_{quiz_id}'].append({
                'content': user_message,
                'is_user': True
            })

            # Generate context for GPT-2
            context = "You are a helpful tutor. Explain the following quiz answers:\n\n"
            for answer in user_answers:  # Using the processed user_answers list
                context += f"Question {answer['question_number']
                                       }: {answer['question_text']}\n"
                context += f"Your answer: {answer['selected_answer']}\n"
                context += f"Correct answer: {answer['correct_answer']}\n"
                context += f"Status: {
                    'Correct' if answer['is_correct'] else 'Incorrect'}\n\n"

            context += f"Student question: {user_message}\n"
            context += "Provide a clear, helpful explanation focusing on understanding the concepts:\n"

            # Generate response using GPT-2
            input_ids = tokenizer.encode(context, return_tensors='pt')
            attention_mask = torch.ones(input_ids.shape, dtype=torch.long)

            with torch.no_grad():
                output = model.generate(
                    input_ids,
                    attention_mask=attention_mask,
                    max_length=200,
                    num_return_sequences=1,
                    no_repeat_ngram_size=2,
                    temperature=0.6,
                    top_p=0.9,
                    pad_token_id=tokenizer.eos_token_id
                )

            response = tokenizer.decode(output[0], skip_special_tokens=True)

            # Post-process the response to ensure it's helpful
            response = format_response(response)

            # Add AI response to chat
            request.session[f'chat_messages_{quiz_id}'].append({
                'content': response,
                'is_user': False
            })

            request.session.modified = True

    return render(request, 'quizzes/quiz_chat.html', {
        'quiz': quiz,
        'user_answers': user_answers,
        'chat_messages': request.session.get(f'chat_messages_{quiz_id}', [])
    })


def analyze_answer(question, user_answer, correct_answer):
    """Analyze the difference between user's answer and correct answer."""
    if question.isdigit() and user_answer.isdigit() and correct_answer.isdigit():
        # For numerical answers
        user_num = int(user_answer)
        correct_num = int(correct_answer)
        diff = abs(user_num - correct_num)
        return f"The difference is {diff}. "
    return ""


def format_response(response):
    """Clean and format the GPT-2 response to be more helpful."""
    # Split response into sentences
    sentences = response.split('.')

    # Keep only relevant sentences (remove generic or off-topic ones)
    relevant_sentences = [s for s in sentences if
                          is_relevant_sentence(s) and
                          len(s.strip()) > 10]

    # Combine sentences and add structure
    if relevant_sentences:
        formatted_response = "Here's the explanation:\n\n"
        formatted_response += ". ".join(relevant_sentences[:3]) + "."
        return formatted_response

    # Fallback response if no good explanation was generated
    return "Let me help you understand this step by step:\n\n" + \
           "1. First, carefully read the question\n" + \
           "2. Break down the problem into smaller parts\n" + \
           "3. Check your calculations again\n" + \
           "Would you like me to explain any specific part in more detail?"


def is_relevant_sentence(sentence):
    """Check if a sentence is relevant to math explanation."""
    relevant_keywords = ['number', 'add', 'subtract', 'equal', 'solution',
                         'answer', 'calculation', 'result', 'step', 'problem',
                         'correct', 'incorrect', 'difference', 'value']
    return any(keyword in sentence.lower() for keyword in relevant_keywords)


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
