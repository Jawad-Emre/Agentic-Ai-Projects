import unittest
from unittest.mock import Mock, patch

from src.gmail.fetch import fetch_unread_emails
from src.gmail.labels import apply_labels_to_email
from src.graph.nodes import finalize_node, is_priority_email


class AgentLogicTests(unittest.TestCase):
    def test_priority_categories_are_protected(self):
        self.assertTrue(is_priority_email({"labels": ["Interview-Invite"], "importance_score": 0.2}))
        self.assertTrue(is_priority_email({"labels": [], "importance_score": 0.8}))
        self.assertFalse(is_priority_email({"labels": ["Newsletter"], "importance_score": 0.3}))

    @patch("src.graph.nodes.mark_as_processed")
    def test_finalize_marks_only_successful_actions(self, mark_as_processed):
        finalize_node({
            "processed": [],
            "handled": [
                {"id": "done", "success": True},
                {"id": "failed", "success": False},
            ],
        })
        mark_as_processed.assert_called_once_with(["done"])

    @patch("src.gmail.labels.get_gmail_service")
    def test_system_labels_are_not_created_as_custom_labels(self, get_service):
        service = Mock()
        get_service.return_value = service
        service.users().labels().list.return_value.execute.return_value = {"labels": []}
        service.users().labels().create.return_value.execute.return_value = {"id": "custom-1"}
        apply_labels_to_email("message-1", ["Needs-Reply", "IMPORTANT", "STARRED"])
        service.users().labels().create.assert_called_once()
        body = service.users().messages().modify.call_args.kwargs["body"]
        self.assertEqual(body["addLabelIds"], ["custom-1", "IMPORTANT", "STARRED"])

    @patch("src.gmail.fetch.get_gmail_service")
    def test_fetch_reads_multiple_pages_up_to_limit(self, get_service):
        service = Mock()
        get_service.return_value = service
        list_execute = service.users().messages().list.return_value.execute
        list_execute.side_effect = [
            {"messages": [{"id": "one"}], "nextPageToken": "next"},
            {"messages": [{"id": "two"}]},
        ]
        service.users().messages().get.return_value.execute.side_effect = [
            {"id": "one", "threadId": "thread-1", "raw": ""},
            {"id": "two", "threadId": "thread-2", "raw": ""},
        ]
        with patch("src.gmail.fetch._parse_raw_message", side_effect=lambda message: message):
            emails = fetch_unread_emails(max_results=2)
        self.assertEqual([email["id"] for email in emails], ["one", "two"])


if __name__ == "__main__":
    unittest.main()