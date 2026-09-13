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

    print("\n=== Run Summary ===")
    print(f"Emails processed: {len(result.get('processed', []))}")
    print(f"Drafts created: {len(result.get('drafted', []))}")
    print("=== Email Agent: Run complete ===")


if __name__ == "__main__":
    main()