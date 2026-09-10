from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from helpdesk.models import FollowUp, Queue, Ticket

from .helpers import get_user


class FollowUpActivityViewTests(TestCase):
    def setUp(self):
        self.user = get_user(username="activity-viewer", is_staff=True)
        self.client.login(username=self.user.get_username(), password="password")
        self.queue = Queue.objects.create(title="Activity", slug="activity")
        self.ticket = Ticket.objects.create(
            title="Activity ticket",
            submitter_email="viewer@example.com",
            queue=self.queue,
        )
        self.followup = FollowUp.objects.create(
            ticket=self.ticket,
            title="Customer replied",
            comment="A normal follow-up comment",
            date=timezone.now(),
            public=True,
            user=self.user,
            message_id="<viewer@example.com>",
            email_recipients=["viewer@example.com"],
        )
        self.url = reverse(
            "helpdesk:followup_activity", args=[self.ticket.id, self.followup.id]
        )

    def test_activity_request_returns_display_fields(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.json()),
            {
                "event",
                "followup_id",
                "ticket_id",
                "date",
                "title",
                "public",
                "new_status",
                "time_spent",
            },
        )
        self.assertEqual(response.json()["followup_id"], self.followup.id)
        self.assertEqual(response.json()["ticket_id"], self.ticket.id)
        self.assertEqual(response.json()["title"], "Customer replied")

    def test_activity_request_requires_matching_ticket(self):
        other_ticket = Ticket.objects.create(
            title="Other ticket",
            submitter_email="other@example.com",
            queue=self.queue,
        )
        url = reverse(
            "helpdesk:followup_activity", args=[other_ticket.id, self.followup.id]
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_followup_edit_page_includes_activity_request(self):
        response = self.client.get(
            reverse("helpdesk:followup_edit", args=[self.ticket.id, self.followup.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.url)
        self.assertContains(response, 'id="followup-activity"')
