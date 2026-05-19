import uuid

from django.conf import settings
from django.db import models
from pgvector.django import VectorField


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    title = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or f"Conversation {self.id}"


class Message(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"
        TOOL = "tool", "Tool"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        preview = self.content[:50].replace("\n", " ")
        return f"[{self.role}] {preview}"


class ToolCall(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="tool_calls",
    )
    tool_name = models.CharField(max_length=100)
    arguments = models.JSONField(default=dict)
    result = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True, default="")
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        status = "error" if self.error else "ok"
        return f"{self.tool_name} ({status})"


class SemanticMemory(models.Model):
    class Category(models.TextChoices):
        PREFERENCE = "preference", "Preference"
        FACT = "fact", "Fact"
        SKILL = "skill", "Skill"
        GOAL = "goal", "Goal"
        CONTEXT = "context", "Context"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="semantic_memories",
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    key = models.CharField(max_length=255)
    value = models.TextField()
    confidence = models.FloatField(default=1.0)
    source_message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="derived_memories",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "category", "key"],
                name="uniq_user_category_key",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "category"]),
        ]

    def __str__(self):
        return f"{self.category}:{self.key} = {self.value[:40]}"


class EpisodicMemory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.OneToOneField(
        Conversation,
        on_delete=models.CASCADE,
        related_name="episode",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="episodic_memories",
    )
    summary = models.TextField()
    topics = models.JSONField(default=list, blank=True)
    key_facts = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "-updated_at"]),
        ]

    def __str__(self):
        return f"Episode of {self.conversation_id}: {self.summary[:50]}"


class MemoryAudit(models.Model):
    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        READ = "read", "Read"

    class MemoryType(models.TextChoices):
        SEMANTIC = "semantic", "Semantic"
        EPISODIC = "episodic", "Episodic"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memory_audits",
    )
    action = models.CharField(max_length=10, choices=Action.choices)
    memory_type = models.CharField(max_length=10, choices=MemoryType.choices)
    memory_id = models.UUIDField(null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["memory_type", "memory_id"]),
        ]

    def __str__(self):
        return f"{self.action} {self.memory_type}:{self.memory_id}"


class KBDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    source_path = models.CharField(max_length=500, blank=True, default="")
    content_hash = models.CharField(max_length=64, unique=True)
    mime_type = models.CharField(max_length=100, blank=True, default="")
    num_chunks = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class KBChunk(models.Model):
    class ChunkType(models.TextChoices):
        PARENT = "parent", "Parent"
        CHILD = "child", "Child"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        KBDocument,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    parent_chunk = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )
    chunk_type = models.CharField(max_length=10, choices=ChunkType.choices)
    chunk_index = models.PositiveIntegerField()
    content = models.TextField()
    token_count = models.PositiveIntegerField(null=True, blank=True)
    embedding = VectorField(dimensions=settings.EMBEDDING_DIM, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["document_id", "chunk_index"]
        indexes = [
            models.Index(fields=["document", "chunk_type"]),
            models.Index(fields=["parent_chunk"]),
        ]

    def __str__(self):
        return f"{self.document.title}#{self.chunk_index} ({self.chunk_type})"


class MessageFeedback(models.Model):
    class Rating(models.TextChoices):
        POSITIVE = "positive", "Positive"
        NEGATIVE = "negative", "Negative"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.OneToOneField(
        Message,
        on_delete=models.CASCADE,
        related_name="feedback",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="message_feedback",
    )
    rating = models.CharField(max_length=10, choices=Rating.choices)
    comment = models.TextField(blank=True, default="")
    categories = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["rating", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.rating} on {self.message_id}"
