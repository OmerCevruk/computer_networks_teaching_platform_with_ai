# admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Quiz, Question, Answer, UserQuestionStatus


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 4
    fields = ['answer_text']


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ["name", "hardness", "question_count"]
    list_filter = ["hardness"]
    search_fields = ["name"]

    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = "Number of Questions"


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["quiz", "question_number",
                    "short_question_text", "hardness", "get_correct_answer"]
    list_filter = ["quiz", "hardness"]
    search_fields = ["question_text"]
    inlines = [AnswerInline]

    def get_correct_answer(self, obj):
        return obj.correct_answer.answer_text if obj.correct_answer else "Not set"
    get_correct_answer.short_description = "Correct Answer"

    def short_question_text(self, obj):
        text = obj.question_text
        if len(text) > 50:
            text = text[:50] + "..."
        return format_html('{}', text)
    short_question_text.short_description = "Question Text"

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            instance.save()
        formset.save_m2m()

        # After all answers are saved, let user select the correct answer
        if not change:  # Only for new questions
            question = form.instance
            if not question.correct_answer and question.answers.exists():
                first_answer = question.answers.first()
                question.correct_answer = first_answer
                question.save()


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ["short_answer_text", "question", "is_correct"]
    list_filter = ["question__quiz"]
    search_fields = ["answer_text", "question__question_text"]

    def short_answer_text(self, obj):
        text = obj.answer_text
        if len(text) > 50:
            text = text[:50] + "..."
        return format_html('{}', text)
    short_answer_text.short_description = "Answer Text"

    def is_correct(self, obj):
        return hasattr(obj, 'correct_for_question')
    is_correct.boolean = True
    is_correct.short_description = "Correct Answer"


@admin.register(UserQuestionStatus)
class UserQuestionStatusAdmin(admin.ModelAdmin):
    list_display = ["user", "get_question", "get_answer"]
    list_filter = ["user", "old_answer__question__quiz"]
    search_fields = ["user__username", "old_answer__answer_text"]

    def get_question(self, obj):
        return obj.old_answer.question
    get_question.short_description = "Question"

    def get_answer(self, obj):
        text = obj.old_answer.answer_text
        if len(text) > 50:
            text = text[:50] + "..."
        return text
    get_answer.short_description = "Answer"
