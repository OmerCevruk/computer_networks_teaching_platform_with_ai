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
    correct_answer = models.OneToOneField(
        'Answer',
        null=True,  # Allow null temporarily
        blank=True,
        on_delete=models.SET_NULL,
        related_name='correct_for_question'
    )

    def __str__(self):
        return f"{self.quiz.name} - Question {self.question_number}"


class Answer(models.Model):
    question = models.ForeignKey(
        Question, related_name='answers', on_delete=models.CASCADE)
    answer_text = models.TextField()

    def __str__(self):
        return self.answer_text


class UserQuestionStatus(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    old_answer = models.ForeignKey(Answer, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "User Question Statuses"
