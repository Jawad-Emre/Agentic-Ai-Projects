# test_fetch.py
from src.gmail.fetch import fetch_unread_emails

emails = fetch_unread_emails(max_results=5)

print(f"Fetched {len(emails)} unread emails:\n")
for e in emails:
    print(f"From: {e['sender']}")
    print(f"Subject: {e['subject']}")
    print(f"Body preview: {e['body'][:150]}...")
    print("-" * 50)