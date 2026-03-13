from django.db import models


class User(models.Model):
    id = models.BigAutoField(primary_key=True)
    login = models.CharField(max_length=100, unique=True)
    password_hash = models.TextField()
    role = models.CharField(max_length=20)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "users"

    def __str__(self):
        return self.login


class Subject(models.Model):
    WORK_TYPES = [
        ("exam", "Exam"),
        ("credit", "Credit"),
        ("course_project", "Course Project"),
    ]

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    work_type = models.CharField(max_length=30, choices=WORK_TYPES)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "subjects"

    def __str__(self):
        return self.name


class Retake(models.Model):
    STATUSES = [
        ("scheduled", "Scheduled"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.BigAutoField(primary_key=True)
    subject = models.ForeignKey(
        Subject,
        models.DO_NOTHING,
        db_column="subject_id",
        related_name="retakes"
    )
    retake_date = models.DateField(null=True, blank=True)
    retake_link = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "retakes"

    def __str__(self):
        return f"{self.subject.name} ({self.status})"


class Statement(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        models.DO_NOTHING,
        db_column="user_id",
        related_name="statements"
    )
    created_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = "statements"

    def __str__(self):
        return f"Statement #{self.id} - {self.user.login}"


class StatementItem(models.Model):
    id = models.BigAutoField(primary_key=True)
    statement = models.ForeignKey(
        Statement,
        models.DO_NOTHING,
        db_column="statement_id",
        related_name="items"
    )
    subject = models.ForeignKey(
        Subject,
        models.DO_NOTHING,
        db_column="subject_id",
        related_name="statement_items"
    )
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "statement_items"

    def __str__(self):
        return f"{self.statement.id} - {self.subject.name}"