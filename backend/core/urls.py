from django.urls import path
from .views import (
    RetakeListView,
    RetakeDetailView,
    CreateStatementFromRetakeView,
    CurrentStatementView,
    StatementListView,
)

urlpatterns = [
    path("retakes/", RetakeListView.as_view(), name="retake-list"),
    path("retakes/<int:retake_id>/", RetakeDetailView.as_view(), name="retake-detail"),
    path(
        "statements/create/<int:retake_id>/",
        CreateStatementFromRetakeView.as_view(),
        name="statement-create-from-retake"
    ),
    path("statements/current/", CurrentStatementView.as_view(), name="statement-current"),
    path("statements/", StatementListView.as_view(), name="statement-list"),
]