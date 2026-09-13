"""
Entry point for the email agent.
Run manually: python main.py
Run via GitHub Actions: scheduled, no manual trigger needed.
"""

from src.graph.build_graph import build_graph


def main():
    print("=== Email Agent: Starting run ===")

    graph = build_graph()
    result = graph.invoke({
        "raw_emails": [],
        "processed": [],
        "drafted": []
    })

    unique_processed = len({e["id"] for e in result.get("processed", [])})
    unique_drafted = len({e["id"] for e in result.get("drafted", [])})

    print("\n=== Run Summary ===")
    print(f"Emails processed: {unique_processed}")
    print(f"Drafts created: {unique_drafted}")
    print("=== Email Agent: Run complete ===")


if __name__ == "__main__":
    main()