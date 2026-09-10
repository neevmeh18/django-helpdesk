from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("helpdesk", "0040_followup_email_recipients"),
    ]

    operations = [
        migrations.CreateModel(
            name="FollowUpActivity",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "event",
                    models.CharField(
                        choices=[("created", "Created"), ("updated", "Updated")],
                        max_length=16,
                        verbose_name="Event",
                    ),
                ),
                (
                    "payload",
                    models.TextField(editable=False, verbose_name="Payload"),
                ),
                (
                    "recorded_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Recorded at"),
                ),
                (
                    "followup",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="activity_records",
                        to="helpdesk.followup",
                        verbose_name="Follow-up",
                    ),
                ),
            ],
            options={
                "verbose_name": "Follow-up activity",
                "verbose_name_plural": "Follow-up activities",
                "ordering": ("recorded_at", "id"),
            },
        ),
    ]
