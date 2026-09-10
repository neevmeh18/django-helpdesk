"""Signals for follow-up activity archiving."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .activity_archive import archive_followup
from .models import FollowUp, FollowUpActivity


@receiver(post_save, sender=FollowUp)
def archive_followup_on_save(sender, instance, created, raw=False, **kwargs):
    if raw:
        return

    event = (
        FollowUpActivity.EVENT_CREATED if created else FollowUpActivity.EVENT_UPDATED
    )
    archive_followup(instance, event)
