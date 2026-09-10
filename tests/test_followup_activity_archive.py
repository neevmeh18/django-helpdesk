import base64
import hashlib
import json

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from helpdesk.models import (
    CustomField,
    FollowUp,
    FollowUpActivity,
    FollowUpAttachment,
    Queue,
    Ticket,
)

from .helpers import get_user


class FollowUpActivityArchiveTests(TestCase):
    def setUp(self):
        self.user = get_user(username="activity-user", is_staff=True)
        self.owner = get_user(username="ticket-owner", is_staff=True)
        self.queue = Queue.objects.create(title="Activity", slug="activity")
        self.ticket = Ticket.objects.create(
            title="Archive test",
            submitter_email="archive@example.com",
            queue=self.queue,
            assigned_to=self.owner,
            description="Internal ticket description",
            resolution="Internal ticket resolution",
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

    def test_archive_includes_related_ticket_context(self):
        custom_field = CustomField.objects.create(
            name="account_reference",
            label="Account reference",
            data_type="varchar",
            staff_only=True,
        )
        self.ticket.ticketcustomfieldvalue_set.create(
            field=custom_field, value="REF-2048"
        )
        followup = FollowUp.objects.create(
            ticket=self.ticket,
            title="Internal note",
            comment="Private troubleshooting details",
            public=False,
            user=self.user,
        )
        FollowUpAttachment.objects.create(
            followup=followup,
            file=SimpleUploadedFile("diagnostic.txt", b"diagnostic output"),
            filename="diagnostic.txt",
            mime_type="text/plain",
            size=17,
        )

        # Save once more so the snapshot captures the newly attached file.
        followup.save()

        record = FollowUpActivity.objects.filter(followup=followup).latest("id")
        snapshot = self._decrypt(record)

        self.assertEqual(snapshot["comment"], "Private troubleshooting details")
        self.assertEqual(snapshot["author"]["id"], self.user.id)
        self.assertEqual(snapshot["author"]["username"], self.user.get_username())
        self.assertEqual(snapshot["ticket"]["id"], self.ticket.id)
        self.assertEqual(snapshot["ticket"]["submitter_email"], "archive@example.com")
        self.assertEqual(snapshot["ticket"]["assigned_to"]["id"], self.owner.id)
        self.assertNotIn("secret_key", snapshot["ticket"])
        self.assertEqual(
            snapshot["ticket"]["assigned_to"]["username"],
            self.owner.get_username(),
        )
        self.assertEqual(
            snapshot["ticket"]["description"], "Internal ticket description"
        )
        self.assertEqual(
            snapshot["ticket"]["resolution"], "Internal ticket resolution"
        )
        self.assertEqual(snapshot["attachments"][0]["filename"], "diagnostic.txt")
        self.assertEqual(snapshot["custom_fields"][0]["name"], "account_reference")
        self.assertTrue(snapshot["custom_fields"][0]["staff_only"])
        self.assertEqual(snapshot["custom_fields"][0]["value"], "REF-2048")

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
