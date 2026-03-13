from django.db import models


class User(models.Model):
    id = models.BigAutoField(primary_key=True)
    login = models.CharField("Логин", max_length=100, unique=True)
    password_hash = models.TextField("Хэш пароля")
    role = models.CharField("Роль", max_length=20)
    created_at = models.DateTimeField("Дата создания")
    updated_at = models.DateTimeField("Дата обновления")

    class Meta:
        managed = False
        db_table = "users"
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.login


class Subject(models.Model):
    WORK_TYPES = [
        ("exam", "Экзамен"),
        ("credit", "Зачёт"),
        ("course_project", "Курсовой проект"),
    ]

    id = models.BigAutoField(primary_key=True)
    name = models.CharField("Название", max_length=255)
    work_type = models.CharField("Тип работы", max_length=50, choices=WORK_TYPES)
    created_at = models.DateTimeField("Дата создания")
    updated_at = models.DateTimeField("Дата обновления")

    class Meta:
        managed = False
        db_table = "subjects"
        verbose_name = "Предмет"
        verbose_name_plural = "Предметы"

    def __str__(self):
        return self.name


class Retake(models.Model):
    STATUSES = [
        ("scheduled", "Запланировано"),
        ("completed", "Завершено"),
        ("cancelled", "Отменено"),
    ]

    id = models.BigAutoField(primary_key=True)
    subject = models.ForeignKey(
        Subject,
        models.DO_NOTHING,
        db_column="subject_id",
        related_name="retakes",
        verbose_name="Предмет",
    )
    retake_date = models.DateField("Дата пересдачи", null=True, blank=True)
    retake_link = models.TextField("Ссылка на пересдачу", null=True, blank=True)
    retake_time = models.TimeField("Время пересдачи", null=True, blank=True)
    lecturer = models.CharField("Преподаватель", max_length=255, null=True, blank=True)
    commission = models.CharField("Комиссия", max_length=255, null=True, blank=True)
    status = models.CharField("Статус", max_length=20, choices=STATUSES)
    created_at = models.DateTimeField("Дата создания")
    updated_at = models.DateTimeField("Дата обновления")

    class Meta:
        managed = False
        db_table = "retakes"
        verbose_name = "Пересдача"
        verbose_name_plural = "Пересдачи"

    def __str__(self):
        return f"{self.subject.name} ({self.status})"


class Statement(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        models.DO_NOTHING,
        db_column="user_id",
        related_name="statements",
        verbose_name="Пользователь",
    )
    created_at = models.DateTimeField("Дата создания")
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        managed = False
        db_table = "statements"
        verbose_name = "Ведомость"
        verbose_name_plural = "Ведомости"

    def __str__(self):
        return f"Ведомость #{self.id} - {self.user.login}"


class StatementItem(models.Model):
    id = models.BigAutoField(primary_key=True)
    statement = models.ForeignKey(
        Statement,
        models.DO_NOTHING,
        db_column="statement_id",
        related_name="items",
        verbose_name="Ведомость",
    )
    subject = models.ForeignKey(
        Subject,
        models.DO_NOTHING,
        db_column="subject_id",
        related_name="statement_items",
        verbose_name="Предмет",
    )
    created_at = models.DateTimeField("Дата создания")

    class Meta:
        managed = False
        db_table = "statement_items"
        verbose_name = "Элемент ведомости"
        verbose_name_plural = "Элементы ведомости"

    def __str__(self):
        return f"{self.statement.id} - {self.subject.name}"