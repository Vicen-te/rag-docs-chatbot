from __future__ import annotations

from rest_framework import serializers

from agent.models import (
    Conversation,
    Message,
    MessageFeedback,
    SemanticMemory,
)


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ("id", "role", "content", "created_at", "metadata")
        read_only_fields = ("id", "created_at")


class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ("id", "title", "created_at", "updated_at", "metadata", "messages")
        read_only_fields = ("id", "created_at", "updated_at", "messages")


class ChatRequestSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField(required=False, allow_null=True)
    message = serializers.CharField()


class KBSearchSerializer(serializers.Serializer):
    query = serializers.CharField()
    top_k = serializers.IntegerField(
        required=False, default=5, min_value=1, max_value=50,
    )
    mode = serializers.ChoiceField(
        choices=["semantic", "lexical", "hybrid"],
        required=False,
        default="hybrid",
    )


class KBSearchHitSerializer(serializers.Serializer):
    chunk_id = serializers.CharField()
    document_id = serializers.CharField()
    content = serializers.CharField()
    score = serializers.FloatField()
    parent_id = serializers.CharField(allow_null=True)
    chunk_type = serializers.CharField()


class SemanticMemorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SemanticMemory
        fields = (
            "id", "category", "key", "value", "confidence",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class MessageFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageFeedback
        fields = (
            "id", "message", "rating", "comment", "categories", "created_at",
        )
        read_only_fields = ("id", "created_at")
