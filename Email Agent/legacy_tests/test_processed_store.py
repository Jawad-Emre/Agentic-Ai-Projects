from src.gmail.fetch import fetch_unread_emails
from src.storage.processed_store import (
    filter_unprocessed,
    mark_as_processed,
    get_processed_ids
)

# Step 1: fetch a small batch
emails = fetch_unread_emails(max_results=5)
print(f"Fetched {len(emails)} emails total.\n")

# Step 2: check what's already processed (should be empty first run)
already_processed = get_processed_ids()
print(f"Already processed: {len(already_processed)} IDs\n")

# Step 3: filter
new_emails = filter_unprocessed(emails)
print(f"New (unprocessed) emails: {len(new_emails)}")
for e in new_emails:
    print(f"  - {e['subject']}")

# Step 4: mark them as processed
mark_as_processed([e["id"] for e in new_emails])
print(f"\nMarked {len(new_emails)} emails as processed.")

# Step 5: run filter again — should now return 0 new emails
new_emails_second_pass = filter_unprocessed(emails)
print(f"\nSecond pass (should be 0): {len(new_emails_second_pass)} new emails")