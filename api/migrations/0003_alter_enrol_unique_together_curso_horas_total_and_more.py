import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_userprofile'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1) СНАЧАЛА реально добавляем колонку codigo в БД
        migrations.AddField(
            model_name='enrol',
            name='codigo',
            field=models.CharField(max_length=64, blank=True, default=''),
        ),

        # 2) Теперь можно менять unique_together
        migrations.AlterUniqueTogether(
            name='enrol',
            unique_together={('user', 'codigo', 'role')},
        ),

        # 3) Новые поля курса
        migrations.AddField(
            model_name='curso',
            name='modules',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='curso',
            name='horas_total',
            field=models.PositiveIntegerField(default=0),
        ),

        # 4) Флаг is_teacher в профиле
        migrations.AddField(
            model_name='userprofile',
            name='is_teacher',
            field=models.BooleanField(default=False),
        ),

        # 5) Мелкие изменения полей
        migrations.AlterField(
            model_name='curso',
            name='descripcion',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='enrol',
            name='role',
            field=models.CharField(
                choices=[('teacher', 'Teacher'), ('student', 'Student')],
                default='student',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='enrol',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='enrolments',
                to=settings.AUTH_USER_MODEL,
            ),
        ),

        # 6) Убираем старое поле curso (FK) из Enrol
        migrations.RemoveField(
            model_name='enrol',
            name='curso',
        ),
    ]
