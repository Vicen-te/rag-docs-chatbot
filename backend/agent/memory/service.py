"""Read/write API for semantic and episodic memory.

Every write appends a row to MemoryAudit so the agent's mutations
can be traced after the fact.
"""
from __future__ import annotations

from django.db import transaction

from agent.models import EpisodicMemory, MemoryAudit, SemanticMemory


def store_semantic(
    user,
    category: str,
    key: str,
    value: str,
    *,
    confidence: float = 1.0,
    source_message=None,
) -> SemanticMemory:
    """UPSERT a semantic fact for the user and record the change."""
    with transaction.atomic():
        mem, created = SemanticMemory.objects.update_or_create(
            user=user,
            category=category,
            key=key,
            defaults={
                "value": value,
                "confidence": confidence,
                "source_message": source_message,
            },
        )
        MemoryAudit.objects.create(
            user=user,
            action=(
                MemoryAudit.Action.CREATE
                if created
                else MemoryAudit.Action.UPDATE
            ),
            memory_type=MemoryAudit.MemoryType.SEMANTIC,
            memory_id=mem.id,
            payload={
                "category": category,
                "key": key,
                "value": value,
                "confidence": confidence,
            },
        )
    return mem


def recall_semantic(
    user,
    category: str | None = None,
    key: str | None = None,
    limit: int = 50,
) -> list[SemanticMemory]:
    qs = SemanticMemory.objects.filter(user=user)
    if category:
        qs = qs.filter(category=category)
    if key:
        qs = qs.filter(key=key)
    return list(qs.order_by("-updated_at")[:limit])


def recall_episodic(user, limit: int = 5) -> list[EpisodicMemory]:
    return list(
        EpisodicMemory.objects.filter(user=user).order_by("-updated_at")[:limit]
    )


def store_episodic(
    user,
    conversation,
    summary: str,
    topics: list[str] | None = None,
    key_facts: list[str] | None = None,
) -> EpisodicMemory:
    """Create or update the episodic summary for a conversation."""
    with transaction.atomic():
        episode, created = EpisodicMemory.objects.update_or_create(
            conversation=conversation,
            defaults={
                "user": user,
                "summary": summary,
                "topics": topics or [],
                "key_facts": key_facts or [],
            },
        )
        MemoryAudit.objects.create(
            user=user,
            action=(
                MemoryAudit.Action.CREATE
                if created
                else MemoryAudit.Action.UPDATE
            ),
            memory_type=MemoryAudit.MemoryType.EPISODIC,
            memory_id=episode.id,
            payload={
                "conversation_id": str(conversation.id),
                "summary": summary,
                "topics": topics or [],
                "key_facts": key_facts or [],
            },
        )
    return episode


def format_memory_for_prompt(
    user,
    max_facts: int = 10,
    max_episodes: int = 3,
) -> str:
    """Render the user's recent memory as a system-prompt snippet."""
    facts = recall_semantic(user, limit=max_facts)
    episodes = recall_episodic(user, limit=max_episodes)

    sections = []
    if facts:
        lines = [f"- [{f.category}] {f.key}: {f.value}" for f in facts]
        sections.append("Known facts about the user:\n" + "\n".join(lines))
    if episodes:
        lines = [f"- {e.summary}" for e in episodes]
        sections.append("Recent conversation summaries:\n" + "\n".join(lines))
    return "\n\n".join(sections)
