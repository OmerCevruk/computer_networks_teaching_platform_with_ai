from django.contrib import admin
from django.utils.html import format_html
from .models import Quiz, Question, UserQuestionStatus, Course, CourseProgress


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at',
                    'updated_at', 'student_count']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['name', 'description']
    # Automatically generate slug from name
    prepopulated_fields = {'slug': ('name',)}
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description')
        }),
        ('Metadata', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    readonly_fields = ['created_at', 'updated_at']

    def student_count(self, obj):
        return CourseProgress.objects.filter(course=obj).count()
    student_count.short_description = 'Enrolled Students'


@admin.register(CourseProgress)
class CourseProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'completed', 'last_accessed']
    list_filter = ['completed', 'last_accessed', 'course']
    search_fields = ['user__username', 'course__name']
    raw_id_fields = ['user', 'course']

    readonly_fields = ['last_accessed']

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ['user', 'course']
        return self.readonly_fields


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
    list_display = [
        "quiz",
        "question_number",
        "short_question_text",
        "hardness",
        "get_correct_answer"
    ]
    list_filter = ["quiz", "hardness"]
    search_fields = ["question_text"]

    fieldsets = (
        (None, {
            'fields': ('quiz', 'question_number', 'question_text', 'hardness')
        }),
        ('Answer Choices', {
            'fields': (
                'answer_1',
                'answer_2',
                'answer_3',
                'answer_4',
                'correct_answer'
            )
        }),
    )

    def get_correct_answer(self, obj):
        answers = {
            1: obj.answer_1,
            2: obj.answer_2,
            3: obj.answer_3,
            4: obj.answer_4
        }
        correct_text = answers.get(obj.correct_answer, "Not set")
        if len(correct_text) > 50:
            correct_text = correct_text[:50] + "..."
        return format_html('{}', correct_text)
    get_correct_answer.short_description = "Correct Answer"

    def short_question_text(self, obj):
        text = obj.question_text
        if len(text) > 50:
            text = text[:50] + "..."
        return format_html('{}', text)
    short_question_text.short_description = "Question Text"


@admin.register(UserQuestionStatus)
class UserQuestionStatusAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "get_question",
        "get_selected_answer",
        "is_correct"
    ]
    list_filter = [
        "user",
        "question__quiz",
        "selected_answer"
    ]
    search_fields = [
        "user__username",
        "question__question_text"
    ]

    def get_question(self, obj):
        return f"{obj.question.quiz.name} - Q{obj.question.question_number}"
    get_question.short_description = "Question"

    def get_selected_answer(self, obj):
        answers = {
            1: obj.question.answer_1,
            2: obj.question.answer_2,
            3: obj.question.answer_3,
            4: obj.question.answer_4
        }
        selected_text = answers.get(obj.selected_answer, "Not set")
        if len(selected_text) > 50:
            selected_text = selected_text[:50] + "..."
        return format_html('{}', selected_text)
    get_selected_answer.short_description = "Selected Answer"

    def is_correct(self, obj):
        return obj.selected_answer == obj.question.correct_answer
    is_correct.boolean = True
    is_correct.short_description = "Correct"

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return ('user', 'question', 'selected_answer')
        return ()
