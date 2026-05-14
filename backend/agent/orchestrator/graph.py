"""ReAct state graph.

intake -> classify -> (conversational | retrieve -> synthesise -> verify) -> END
The verify node can loop back to synthesise up to AGENT_MAX_VERIFY_RETRIES.
"""
from __future__ import annotations

import json
from typing import TypedDict

from django.conf import settings
from langgraph.graph import END, StateGraph

from agent.kb.search import hybrid_search
from agent.memory.service import format_memory_for_prompt
from agent.orchestrator import prompts
from agent.orchestrator.guardrails import sanitize
from agent.orchestrator.llm_client import chat_completion
from agent.orchestrator.router import classify_task_type, try_fast_route


class AgentState(TypedDict, total=False):
    user_id: str
    conversation_id: str
    user_message: str
    task_type: str
    fast_answer: str | None
    context: list[dict]
    memory_block: str
    candidate: str
    final: str
    verify_iterations: int
    verify_reason: str


def _intake(state: AgentState, config) -> AgentState:
    user = config["configurable"]["user"]
    state["memory_block"] = format_memory_for_prompt(user)
    state["verify_iterations"] = 0
    return state


def _classify(state: AgentState, config) -> AgentState:
    state["task_type"] = classify_task_type(state["user_message"])
    state["fast_answer"] = try_fast_route(state["user_message"])
    return state


def _conversational(state: AgentState, config) -> AgentState:
    if state.get("fast_answer"):
        state["final"] = sanitize(state["fast_answer"])
        return state
    messages = [
        {"role": "system", "content": prompts.CONVERSATIONAL},
        {"role": "user", "content": state["user_message"]},
    ]
    resp = chat_completion(messages=messages, temperature=0.4)
    state["final"] = sanitize(resp["choices"][0]["message"]["content"])
    return state


def _retrieve(state: AgentState, config) -> AgentState:
    hits = hybrid_search(state["user_message"], top_k=settings.AGENT_TOP_K)
    state["context"] = [
        {"document_id": h.document_id, "content": h.content, "score": h.score}
        for h in hits
    ]
    return state


def _synthesise(state: AgentState, config) -> AgentState:
    context_block = "\n\n".join(
        f"[doc:{c['document_id']}]\n{c['content']}"
        for c in state.get("context", [])
    )
    system_prompt = "\n\n".join(
        s for s in (
            prompts.SYSTEM,
            state.get("memory_block") or "",
            prompts.SYNTHESIS,
        ) if s
    )
    user_content = (
        f"Question: {state['user_message']}\n\nContext:\n{context_block}"
    )
    verify_reason = state.get("verify_reason", "")
    if state.get("verify_iterations", 0) > 0 and verify_reason:
        user_content += (
            f"\n\nA previous attempt was rejected for: {verify_reason}\n"
            "Produce a new answer that addresses this issue. "
            "Stay grounded in the context above; do not invent facts."
        )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    resp = chat_completion(messages=messages, temperature=0.2)
    state["candidate"] = resp["choices"][0]["message"]["content"]
    return state


def _verify(state: AgentState, config) -> AgentState:
    messages = [
        {"role": "system", "content": prompts.VERIFY},
        {
            "role": "user",
            "content": (
                f"Question: {state['user_message']}\n\n"
                f"Answer: {state['candidate']}\n\n"
                f"Context: {json.dumps(state.get('context', []))}"
            ),
        },
    ]
    resp = chat_completion(messages=messages, temperature=0.0)
    content = resp["choices"][0]["message"]["content"]
    try:
        parsed = json.loads(content)
        valid = bool(parsed.get("valid", False))
        state["verify_reason"] = parsed.get("reason", "")
    except json.JSONDecodeError:
        # Be lenient when the verifier did not emit valid JSON.
        valid = True
        state["verify_reason"] = "verifier output non-JSON"
    state["verify_iterations"] = state.get("verify_iterations", 0) + 1
    if valid or state["verify_iterations"] >= settings.AGENT_MAX_VERIFY_RETRIES:
        state["final"] = sanitize(state["candidate"])
    return state


def _route_after_classify(state: AgentState) -> str:
    return "conversational" if state["task_type"] == "conversational" else "retrieve"


def _route_after_verify(state: AgentState) -> str:
    return "respond" if "final" in state else "retry"


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("intake", _intake)
    g.add_node("classify", _classify)
    g.add_node("conversational", _conversational)
    g.add_node("retrieve", _retrieve)
    g.add_node("synthesise", _synthesise)
    g.add_node("verify", _verify)

    g.set_entry_point("intake")
    g.add_edge("intake", "classify")
    g.add_conditional_edges("classify", _route_after_classify, {
        "conversational": "conversational",
        "retrieve": "retrieve",
    })
    g.add_edge("conversational", END)
    g.add_edge("retrieve", "synthesise")
    g.add_edge("synthesise", "verify")
    g.add_conditional_edges("verify", _route_after_verify, {
        "respond": END,
        "retry": "synthesise",
    })
    return g.compile()


GRAPH = build_graph()


def run_agent(user, conversation_id, user_message: str) -> AgentState:
    initial: AgentState = {
        "user_id": str(user.id),
        "conversation_id": str(conversation_id),
        "user_message": user_message,
    }
    return GRAPH.invoke(initial, config={"configurable": {"user": user}})
