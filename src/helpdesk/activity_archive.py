"""Follow-up activity archive helpers."""

from __future__ import annotations

import base64
import hashlib
import json

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder


def _archive_key() -> bytes:
    configured_key = getattr(settings, "HELPDESK_ACTIVITY_ARCHIVE_KEY", None)
    if configured_key:
        if isinstance(configured_key, str):
            return configured_key.encode("ascii")
        return configured_key

    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _archive_cipher() -> Fernet:
    return Fernet(_archive_key())


def _user_context(user) -> dict | None:
    if user is None:
        return None
    return {
        "id": user.id,
        "username": user.get_username(),
        "email": user.email,
    }


def _ticket_context(ticket) -> dict:
    return {
        "id": ticket.id,
        "title": ticket.title,
        "queue_id": ticket.queue_id,
        "status": ticket.status,
        "priority": ticket.priority,
        "submitter_email": ticket.submitter_email,
        "assigned_to": _user_context(ticket.assigned_to),
        "description": ticket.description,
        "resolution": ticket.resolution,
    }


def _attachment_context(followup) -> list[dict]:
    return list(
        followup.followupattachment_set.order_by("id").values(
            "id", "filename", "mime_type", "size"
        )
    )


def _custom_field_context(ticket) -> list[dict]:
    values = ticket.ticketcustomfieldvalue_set.select_related("field").order_by(
        "field_id"
    )
    return [
        {
            "field_id": item.field_id,
            "name": item.field.name,
            "label": item.field.label,
            "staff_only": item.field.staff_only,
            "value": item.value,
        }
        for item in values
    ]


def build_followup_snapshot(followup) -> dict:
    """Return the current database-facing state of the follow-up and ticket."""
    snapshot = {
        field.attname: getattr(followup, field.attname)
        for field in followup._meta.concrete_fields
    }
    snapshot.update(
        {
            "author": _user_context(followup.user),
            "ticket": _ticket_context(followup.ticket),
            "attachments": _attachment_context(followup),
            "custom_fields": _custom_field_context(followup.ticket),
        }
    )
    return snapshot


def encode_activity_payload(snapshot: dict) -> str:
    serialized = json.dumps(
        snapshot,
        cls=DjangoJSONEncoder,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return _archive_cipher().encrypt(serialized).decode("ascii")


def archive_followup(followup, event: str):
    """Persist the current follow-up state as an activity record."""
    from .models import FollowUpActivity

    return FollowUpActivity.objects.create(
        followup=followup,
        event=event,
        payload=encode_activity_payload(build_followup_snapshot(followup)),
    )
