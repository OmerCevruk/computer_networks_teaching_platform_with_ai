from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from mainApp.models import Quiz, Question, Answer, UserQuestionStatus
import random

class Command(BaseCommand):
    help = 'Populates the database with sample quiz data'

    def handle(self, *args, **kwargs):
        try:
            with transaction.atomic():
                self.stdout.write('Creating sample data...')

                # Create sample users
                users = []
                for i in range(1, 4):
                    user, created = User.objects.get_or_create(
                        username=f'user{i}',
                        email=f'user{i}@example.com'
                    )
                    if created:
                        user.set_password(f'password{i}')
                        user.save()
                    users.append(user)
                self.stdout.write('Created sample users')

                # Sample quiz data
                quiz_data = [
                    {
                        'name': 'Python Basics',
                        'hardness': 3,
                        'questions': [
                            {
                                'text': 'What is a dictionary in Python?',
                                'hardness': 2,
                                'answers': [
                                    'A data structure that stores key-value pairs',
                                    'A book containing word definitions',
                                    'A list of items',
                                    'A type of loop'
                                ],
                                'correct_index': 0
                            },
                            {
                                'text': 'What does len() function do?',
                                'hardness': 1,
                                'answers': [
                                    'Converts string to lowercase',
                                    'Returns the length of an object',
                                    'Creates a new list',
                                    'Defines a new function'
                                ],
                                'correct_index': 1
                            }
                        ]
                    },
                    {
                        'name': 'Advanced Python',
                        'hardness': 7,
                        'questions': [
                            {
                                'text': 'What is a decorator in Python?',
                                'hardness': 8,
                                'answers': [
                                    'A design pattern',
                                    'A function that modifies another function',
                                    'A type of loop',
                                    'A class attribute'
                                ],
                                'correct_index': 1
                            },
                            {
                                'text': 'What is a generator in Python?',
                                'hardness': 6,
                                'answers': [
                                    'A random number generator',
                                    'A type of function that creates iterators',
                                    'A class constructor',
                                    'A built-in module'
                                ],
                                'correct_index': 1
                            }
                        ]
                    }
                ]

                # Create quizzes
                for quiz_info in quiz_data:
                    quiz = Quiz.objects.create(
                        name=quiz_info['name'],
                        hardness=quiz_info['hardness']
                    )
                    
                    # Create questions for each quiz
                    for q_num, q_info in enumerate(quiz_info['questions'], 1):
                        # First create all answers
                        answers = []
                        for ans_text in q_info['answers']:
                            answer = Answer.objects.create(
                                answer_text=ans_text,
                                question=None  # This is a placeholder; you will associate it with the question later
                            )
                            answers.append(answer)
                        question = Question.objects.create(
                            quiz=quiz,
                            question_number=q_num,
                            question_text=q_info['text'],
                            hardness=q_info['hardness'],
                            correct_answer=answers[q_info['correct_index']]
                        )

                        for answer in answers:
                            answer.question = question
                            answer.save()
                        
                        # Create some user responses
                        for user in users:
                            if random.random() > 0.3:  # 70% chance of answering
                                # Randomly select an answer
                                chosen_answer = random.choice(answers)
                                
                                # Create UserQuestionStatus entry
                                UserQuestionStatus.objects.create(
                                    user=user,
                                    question=question,  # Ensure the question is saved
                                    old_answer=chosen_answer
                                )

                self.stdout.write(self.style.SUCCESS('Successfully populated database'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An error occurred: {str(e)}'))
            raise e
