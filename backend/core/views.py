from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User, Retake, Statement, StatementItem
from .serializers import (
    RetakeListSerializer,
    RetakeDetailSerializer,
    StatementSerializer,
)


class RetakeListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        queryset = Retake.objects.select_related("subject").all().order_by("id")
        serializer = RetakeListSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RetakeDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, retake_id):
        retake = get_object_or_404(
            Retake.objects.select_related("subject"),
            id=retake_id
        )
        serializer = RetakeDetailSerializer(retake)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CreateStatementFromRetakeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, retake_id):
        user_id = request.data.get("user_id")

        if not user_id:
            return Response(
                {"detail": "Поле user_id обязательно."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = get_object_or_404(User, id=user_id)
        retake = get_object_or_404(
            Retake.objects.select_related("subject"),
            id=retake_id
        )

        statement, _ = Statement.objects.get_or_create(
            user=user,
            is_active=True,
            defaults={}
        )

        statement_item, created = StatementItem.objects.get_or_create(
            statement=statement,
            subject=retake.subject,
            defaults={}
        )

        serializer = StatementSerializer(statement)

        return Response(
            {
                "message": (
                    "Предмет добавлен в ведомость."
                    if created
                    else "Предмет уже есть в текущей ведомости."
                ),
                "statement": serializer.data
            },
            status=status.HTTP_200_OK
        )


class CurrentStatementView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        user_id = request.query_params.get("user_id")

        if not user_id:
            return Response(
                {"detail": "Параметр user_id обязателен."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = get_object_or_404(User, id=user_id)

        statement = Statement.objects.filter(
            user=user,
            is_active=True
        ).prefetch_related("items__subject").first()

        if not statement:
            return Response(
                {
                    "message": "У пользователя нет активной ведомости.",
                    "statement": None
                },
                status=status.HTTP_200_OK
            )

        serializer = StatementSerializer(statement)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StatementListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        user_id = request.query_params.get("user_id")

        if not user_id:
            return Response(
                {"detail": "Параметр user_id обязателен."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = get_object_or_404(User, id=user_id)

        statements = Statement.objects.filter(
            user=user
        ).prefetch_related("items__subject").order_by("-created_at")

        serializer = StatementSerializer(statements, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)