from django.contrib import admin

from .models import (
    Conversation,
    EpisodicMemory,
    KBChunk,
    KBDocument,
    Message,
    MemoryAudit,
    MessageFeedback,
    SemanticMemory,
    ToolCall,
)


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ("role", "content", "created_at")
    readonly_fields = ("created_at",)
    show_change_link = True


class ToolCallInline(admin.TabularInline):
    model = ToolCall
    extra = 0
    fields = ("tool_name", "latency_ms", "error", "created_at")
    readonly_fields = ("created_at",)
    show_change_link = True


class KBChunkInline(admin.TabularInline):
    model = KBChunk
    extra = 0
    fields = ("chunk_type", "chunk_index", "token_count", "parent_chunk")
    readonly_fields = ("chunk_type", "chunk_index", "token_count", "parent_chunk")
    show_change_link = True
    can_delete = False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "created_at", "updated_at")
    list_filter = ("user", "created_at")
    search_fields = ("title", "user__username")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "role", "short_content", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("content", "conversation__title")
    readonly_fields = ("id", "created_at")
    inlines = [ToolCallInline]

    @admin.display(description="Content")
    def short_content(self, obj):
        return (obj.content[:80] + "...") if len(obj.content) > 80 else obj.content


@admin.register(ToolCall)
class ToolCallAdmin(admin.ModelAdmin):
    list_display = ("id", "tool_name", "message", "latency_ms", "has_error", "created_at")
    list_filter = ("tool_name", "created_at")
    search_fields = ("tool_name", "error")
    readonly_fields = ("id", "created_at")

    @admin.display(boolean=True, description="Error?")
    def has_error(self, obj):
        return bool(obj.error)


@admin.register(SemanticMemory)
class SemanticMemoryAdmin(admin.ModelAdmin):
    list_display = ("user", "category", "key", "short_value", "confidence", "updated_at")
    list_filter = ("category", "user", "updated_at")
    search_fields = ("key", "value", "user__username")
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("source_message",)

    @admin.display(description="Value")
    def short_value(self, obj):
        return (obj.value[:60] + "...") if len(obj.value) > 60 else obj.value


@admin.register(EpisodicMemory)
class EpisodicMemoryAdmin(admin.ModelAdmin):
    list_display = ("conversation", "user", "short_summary", "updated_at")
    list_filter = ("user", "updated_at")
    search_fields = ("summary", "user__username")
    readonly_fields = ("id", "created_at", "updated_at")

    @admin.display(description="Summary")
    def short_summary(self, obj):
        return (obj.summary[:80] + "...") if len(obj.summary) > 80 else obj.summary


@admin.register(MemoryAudit)
class MemoryAuditAdmin(admin.ModelAdmin):
    list_display = ("user", "action", "memory_type", "memory_id", "created_at")
    list_filter = ("action", "memory_type", "user", "created_at")
    search_fields = ("user__username",)
    readonly_fields = ("id", "user", "action", "memory_type", "memory_id", "payload", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(KBDocument)
class KBDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "mime_type", "num_chunks", "short_hash", "created_at")
    list_filter = ("mime_type", "created_at")
    search_fields = ("title", "source_path", "content_hash")
    readonly_fields = ("id", "content_hash", "num_chunks", "created_at", "updated_at")
    inlines = [KBChunkInline]

    @admin.display(description="Hash")
    def short_hash(self, obj):
        return obj.content_hash[:12] + "..." if obj.content_hash else ""


@admin.register(KBChunk)
class KBChunkAdmin(admin.ModelAdmin):
    list_display = ("document", "chunk_index", "chunk_type", "token_count", "has_embedding")
    list_filter = ("chunk_type", "document")
    search_fields = ("content", "document__title")
    readonly_fields = ("id", "created_at")
    autocomplete_fields = ("document", "parent_chunk")

    @admin.display(boolean=True, description="Embedded?")
    def has_embedding(self, obj):
        return obj.embedding is not None


@admin.register(MessageFeedback)
class MessageFeedbackAdmin(admin.ModelAdmin):
    list_display = ("message", "user", "rating", "categories", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("comment", "user__username")
    readonly_fields = ("id", "created_at")
