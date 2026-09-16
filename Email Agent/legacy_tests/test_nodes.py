from src.gmail.fetch import fetch_unread_emails
from src.graph.nodes import classify_and_score

emails = fetch_unread_emails(max_results=5)

for email in emails:
    result = classify_and_score(email)
    classified = result["processed"][0]
    print(f"Subject: {classified['subject']}")
    print(f"  Labels: {classified['labels']}")
    print(f"  Importance: {classified['importance_score']}")
    print(f"  Needs Reply: {classified['needs_reply']}")
    print(f"  Reasoning: {classified['reasoning']}")
    print("-" * 60)