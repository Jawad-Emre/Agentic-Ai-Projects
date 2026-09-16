from src.gmail.fetch import fetch_unread_emails
from src.graph.nodes import classify_and_score
from src.gmail.labels import apply_labels_batch

emails = fetch_unread_emails(max_results=3)

classified_emails = []
for email in emails:
    result = classify_and_score(email)
    classified_emails.append(result["processed"][0])

apply_labels_batch(classified_emails)

print("\nDone. Check your Gmail — these 3 emails should now have labels applied.")