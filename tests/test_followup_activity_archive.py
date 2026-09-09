import base64
import hashlib
import json

from cryptography.fernet import Fernet
from django.conf import settings
from django.test import TestCase

from helpdesk.models import FollowUp, FollowUpActivity, Queue, Ticket

from .helpers import get_user


class FollowUpActivityArchiveTests(TestCase):
    def setUp(self):
        self.user = get_user(username="activity-user", is_staff=True)
        self.queue = Queue.objects.create(title="Activity", slug="activity")
        self.ticket = Ticket.objects.create(
            title="Archive test",
            submitter_email="archive@example.com",
            queue=self.queue,
        )

    def _decrypt(self, record):
        configured_key = getattr(settings, "HELPDESK_ACTIVITY_ARCHIVE_KEY", None)
        if configured_key:
            key = (
                configured_key.encode("ascii")
                if isinstance(configured_key, str)
                else configured_key
            )
        else:
            key = base64.urlsafe_b64encode(
                hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
            )
        plaintext = Fernet(key).decrypt(record.payload.encode("ascii"))
        return json.loads(plaintext.decode("utf-8"))

    def test_create_archives_followup_snapshot(self):
        followup = FollowUp.objects.create(
            ticket=self.ticket,
            title="Initial activity",
            comment="Initial comment",
            public=False,
            user=self.user,
            message_id="<activity@example.com>",
        )

        record = FollowUpActivity.objects.get(followup=followup)
        self.assertEqual(record.event, FollowUpActivity.EVENT_CREATED)

        snapshot = self._decrypt(record)
        self.assertEqual(snapshot["id"], followup.id)
        self.assertEqual(snapshot["ticket_id"], self.ticket.id)
        self.assertEqual(snapshot["title"], "Initial activity")
        self.assertEqual(snapshot["comment"], "Initial comment")
        self.assertEqual(snapshot["user_id"], self.user.id)
        self.assertEqual(snapshot["message_id"], "<activity@example.com>")

    def test_update_adds_another_activity_record(self):
        followup = FollowUp.objects.create(
            ticket=self.ticket,
            title="Before",
            comment="Before comment",
            user=self.user,
        )

        followup.title = "After"
        followup.comment = "After comment"
        followup.save()

        records = list(FollowUpActivity.objects.filter(followup=followup))
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].event, FollowUpActivity.EVENT_CREATED)
        self.assertEqual(records[1].event, FollowUpActivity.EVENT_UPDATED)
        self.assertEqual(self._decrypt(records[1])["comment"], "After comment")


    def test_activity_record_survives_followup_deletion(self):
        followup = FollowUp.objects.create(
            ticket=self.ticket,
            title="Temporary follow-up",
            comment="Archived before deletion",
            user=self.user,
        )
        record = FollowUpActivity.objects.get(followup=followup)

        followup.delete()

        record.refresh_from_db()
        self.assertIsNone(record.followup_id)
        self.assertEqual(self._decrypt(record)["comment"], "Archived before deletion")

    def test_payload_is_not_stored_as_plain_text(self):
        followup = FollowUp.objects.create(
            ticket=self.ticket,
            title="Visible title marker",
            comment="Visible comment marker",
            user=self.user,
        )

        record = FollowUpActivity.objects.get(followup=followup)
        self.assertNotIn("Visible title marker", record.payload)
        self.assertNotIn("Visible comment marker", record.payload)
        self.assertNotIn("archive@example.com", record.payload)
