from src.gmail.fetch import fetch_unread_emails
from src.graph.nodes import classify_and_score, draft_reply
from src.gmail.drafts import create_draft_reply

emails = fetch_unread_emails(max_results=10)

for email in emails:
    result = classify_and_score(email)
    classified = result["processed"][0]

    print(f"Subject: {classified['subject']} | needs_reply: {classified['needs_reply']}")

    if classified["needs_reply"]:
        drafted = draft_reply(classified)
        print(f"  Generated draft:\n  {drafted['draft']}\n")

        create_draft_reply(drafted)
        print(f"  ✅ Draft saved to Gmail for: {classified['subject']}")

    print("-" * 60)