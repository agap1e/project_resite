from django.contrib import admin
from .models import User, Subject, Retake, Statement, StatementItem


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "login", "role", "created_at")
    search_fields = ("login", "role")
    list_filter = ("role",)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "work_type", "created_at")
    search_fields = ("name",)
    list_filter = ("work_type",)


@admin.register(Retake)
class RetakeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "subject",
        "retake_date",
        "retake_time",
        "lecturer",
        "commission",
        "status",
    )
    search_fields = ("subject__name",)
    list_filter = ("status", "retake_date")


@admin.register(Statement)
class StatementAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at", "is_active")
    search_fields = ("user__login",)
    list_filter = ("is_active", "created_at")


@admin.register(StatementItem)
class StatementItemAdmin(admin.ModelAdmin):
    list_display = ("id", "statement", "subject", "created_at")
    search_fields = ("subject__name", "statement__user__login")
    list_filter = ("created_at",)