from django.db import models
from django.contrib.auth.models import User


class Quiz(models.Model):
    name = models.CharField(max_length=200)
    hardness = models.IntegerField()

    def __str__(self):
        return self.name


class Question(models.Model):
    quiz = models.ForeignKey(
        Quiz, related_name='questions', on_delete=models.CASCADE)
    question_number = models.IntegerField()
    question_text = models.TextField()
    hardness = models.IntegerField()

    answer_1 = models.TextField(default="Option 1")
    answer_2 = models.TextField(default="Option 2")
    answer_3 = models.TextField(default="Option 3")
    answer_4 = models.TextField(default="Option 4")
    correct_answer = models.IntegerField(
        choices=[
            (1, 'Answer 1'),
            (2, 'Answer 2'),
            (3, 'Answer 3'),
            (4, 'Answer 4'),
        ],
        default=1
    )

    def __str__(self):
        return f"{self.quiz.name} - Question {self.question_number}"


class UserQuestionStatus(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    old_answer = models.ForeignKey(
        'Answer', on_delete=models.CASCADE, null=True, blank=True)  # Make this nullable
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, null=True, blank=True)  # Make this nullable
    selected_answer = models.IntegerField(
        choices=[
            (1, 'Answer 1'),
            (2, 'Answer 2'),
            (3, 'Answer 3'),
            (4, 'Answer 4'),
        ],
        null=True,  # Make this nullable
        blank=True
    )

    class Meta:
        verbose_name_plural = "User Question Statuses"

# Keep the old Answer model temporarily


class Answer(models.Model):
    question = models.ForeignKey(
        Question, related_name='answers', on_delete=models.CASCADE)
    answer_text = models.TextField()

    def __str__(self):
        return self.answer_text
