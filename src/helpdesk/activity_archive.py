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


def build_followup_snapshot(followup) -> dict:
    """Return the current database-facing state of the follow-up."""
    return {
        field.attname: getattr(followup, field.attname)
        for field in followup._meta.concrete_fields
    }


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
