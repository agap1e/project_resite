from django.contrib import admin
from .models import User, Subject, Retake, Statement, StatementItem

admin.site.register(User)
admin.site.register(Subject)
admin.site.register(Retake)
admin.site.register(Statement)
admin.site.register(StatementItem)