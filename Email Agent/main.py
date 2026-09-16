"""
Entry point for the email agent.
Run manually: python main.py
Run via GitHub Actions: scheduled, no manual trigger needed.
"""

from collections import Counter
from src.graph.build_graph import build_graph


def main():
    print("=== Email Agent: Starting run ===")

    graph = build_graph()
    result = graph.invoke({
        "raw_emails": [],
        "processed": [],
        "handled": []
    })

    unique_processed = len({
        h["id"] for h in result.get("handled", []) if h.get("success") is True
    })

    # Dedupe by email id before counting actions — Send() fan-out can
    # produce multiple log entries per email even though the actual
    # tool only executes once per email in practice.
    handled_by_id = {h["id"]: h for h in result.get("handled", [])}
    unique_handled = len(handled_by_id)
    action_counts = Counter(h.get("action", "unknown") for h in handled_by_id.values())
    failed = sum(1 for h in handled_by_id.values() if h.get("success") is not True)

    print("\n=== Run Summary ===")
    print(f"Emails processed: {unique_processed}")
    print(f"Actions taken: {unique_handled}")
    print(f"Actions failed (will retry): {failed}")
    for action, count in action_counts.items():
        print(f"  - {action}: {count}")
    print("=== Email Agent: Run complete ===")


if __name__ == "__main__":
    main()