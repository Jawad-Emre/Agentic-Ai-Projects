from src.graph.build_graph import build_graph

graph = build_graph()

result = graph.invoke({"raw_emails": [], "processed": [], "drafted": []})

print("\n--- Run complete ---")
print(f"Processed: {len(result['processed'])} emails")
print(f"Drafted: {len(result['drafted'])} replies")