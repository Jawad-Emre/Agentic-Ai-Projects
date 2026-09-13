"""
Assembles all nodes and edges into the compiled LangGraph agent.
"""

from langgraph.graph import StateGraph, START, END
from src.graph.state import GraphState
from src.graph.nodes import (
    fetch_unread_node,
    classify_and_score,
    apply_labels_node,
    run_agent_for_email,
    finalize_node,
)
from src.graph.edges import route_to_classification, route_to_agent


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("fetch_unread", fetch_unread_node)
    graph.add_node("classify_and_score", classify_and_score)
    graph.add_node("apply_labels", apply_labels_node)
    graph.add_node("run_agent_for_email", run_agent_for_email)
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "fetch_unread")
    graph.add_conditional_edges("fetch_unread", route_to_classification, ["classify_and_score"])
    graph.add_edge("classify_and_score", "apply_labels")
    graph.add_conditional_edges("apply_labels", route_to_agent, ["run_agent_for_email"])
    graph.add_edge("run_agent_for_email", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()