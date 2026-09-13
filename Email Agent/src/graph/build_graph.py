"""
Assembles all nodes and edges into the compiled LangGraph agent.
"""

from langgraph.graph import StateGraph, START, END
from src.graph.state import GraphState
from src.graph.nodes import (
    fetch_unread_node,
    classify_and_score,
    apply_labels_node,
    draft_reply_node,
    skip_drafting_node,
    finalize_node,
)
from src.graph.edges import route_to_classification, route_to_drafting


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("fetch_unread", fetch_unread_node)
    graph.add_node("classify_and_score", classify_and_score)
    graph.add_node("apply_labels", apply_labels_node)
    graph.add_node("draft_reply_node", draft_reply_node)
    graph.add_node("skip_drafting", skip_drafting_node)
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "fetch_unread")
    graph.add_conditional_edges(
        "fetch_unread", route_to_classification, ["classify_and_score"]
    )
    graph.add_edge("classify_and_score", "apply_labels")
    graph.add_conditional_edges(
        "apply_labels", route_to_drafting, ["draft_reply_node", "skip_drafting"]
    )
    graph.add_edge("draft_reply_node", "finalize")
    graph.add_edge("skip_drafting", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()