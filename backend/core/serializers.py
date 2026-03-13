from rest_framework import serializers
from .models import User, Subject, Retake, Statement, StatementItem


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "login", "role"]


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ["id", "name", "work_type"]


class RetakeListSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)

    class Meta:
        model = Retake
        fields = [
            "id",
            "subject",
            "retake_date",
            "retake_link",
            "status",
            "created_at",
            "updated_at",
            "retake_time",
            "lecturer",
            "commission",
        ]


class RetakeDetailSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)

    class Meta:
        model = Retake
        fields = [
            "id",
            "subject",
            "retake_date",
            "retake_link",
            "retake_time",
            "lecturer",
            "commission",
            "status",
            "created_at",
            "updated_at",
        ]


class StatementItemSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)

    class Meta:
        model = StatementItem
        fields = ["id", "subject", "created_at"]


class StatementSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    items = StatementItemSerializer(many=True, read_only=True)

    class Meta:
        model = Statement
        fields = ["id", "user", "created_at", "is_active", "items"]