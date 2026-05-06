from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.llm.nodes import (
    ChatGraphState,
    evaluate_affinity_node,
    guardrail_node,
    retrieve_context_node,
)


def _build_graph():
    g = StateGraph(ChatGraphState)
    g.add_node("retrieve_context", retrieve_context_node)
    g.add_node("guardrail", guardrail_node)
    g.add_node("evaluate_affinity", evaluate_affinity_node)
    g.add_edge(START, "retrieve_context")
    g.add_edge("retrieve_context", "guardrail")
    g.add_edge("guardrail", "evaluate_affinity")
    g.add_edge("evaluate_affinity", END)
    return g.compile()


@lru_cache(maxsize=1)
def get_graph():
    return _build_graph()
