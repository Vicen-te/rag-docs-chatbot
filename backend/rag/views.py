from __future__ import annotations

from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rag.kb.search import hybrid_search
from rag.models import Conversation, Message, MessageFeedback, SemanticMemory
from rag.orchestrator.graph import stream_pipeline
from rag.orchestrator.streaming import (
    format_sse_event,
    sse_done,
    sse_error,
    sse_step,
    sse_token,
)
from rag.serializers import (
    ChatRequestSerializer,
    ConversationSerializer,
    KBSearchHitSerializer,
    KBSearchSerializer,
    MessageFeedbackSerializer,
    SemanticMemorySerializer,
)


class ChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = ChatRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = request.user
        data = request.data
        regenerate_id = data.get("regenerate_assistant_message_id")

        if regenerate_id:
            old_assistant = get_object_or_404(
                Message,
                id=regenerate_id,
                role=Message.Role.ASSISTANT,
                conversation__user=user,
            )
            conversation = old_assistant.conversation
            user_msg = (
                Message.objects
                .filter(
                    conversation=conversation,
                    role=Message.Role.USER,
                    created_at__lt=old_assistant.created_at,
                )
                .order_by("-created_at")
                .first()
            )
            if user_msg is None:
                return Response(
                    {"detail": "no user message precedes the assistant message"},
                    status=400,
                )
            user_text = user_msg.content
            # Regenerating a non-last assistant turn rewrites history
            # from that point: drop the old assistant and every message
            # that came after it, then stream a fresh answer in its place.
            Message.objects.filter(
                conversation=conversation,
                created_at__gte=old_assistant.created_at,
            ).delete()
        else:
            conv_id = data.get("conversation_id")
            if conv_id:
                conversation = get_object_or_404(
                    Conversation, id=conv_id, user=user,
                )
            else:
                conversation = Conversation.objects.create(user=user)
            user_text = data["message"]
            user_msg = Message.objects.create(
                conversation=conversation,
                role=Message.Role.USER,
                content=user_text,
            )
            if not conversation.title:
                title = user_text.strip().splitlines()[0][:60]
                if title:
                    conversation.title = title
                    conversation.save(update_fields=["title", "updated_at"])

        def stream():
            try:
                yield format_sse_event("meta", {
                    "conversation_id": str(conversation.id),
                    "user_message_id": str(user_msg.id),
                })
                final = ""
                for ev in stream_pipeline(user, conversation.id, user_text):
                    if ev["type"] == "step":
                        yield sse_step(ev["node"], ev["diff"], ev["state"])
                    else:
                        final = ev["state"].get("final", "")
                for token in final.split(" "):
                    yield sse_token(token + " ")
                assistant_msg = Message.objects.create(
                    conversation=conversation,
                    role=Message.Role.ASSISTANT,
                    content=final,
                )
                yield sse_done({
                    "conversation_id": str(conversation.id),
                    "assistant_message_id": str(assistant_msg.id),
                })
            except Exception as exc:
                yield sse_error(str(exc))

        return StreamingHttpResponse(stream(), content_type="text/event-stream")


class KBSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ser = KBSearchSerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        hits = hybrid_search(**ser.validated_data)
        payload = [
            {
                "chunk_id": h.chunk_id,
                "document_id": h.document_id,
                "content": h.content,
                "score": h.score,
                "parent_id": h.parent_id,
                "chunk_type": h.chunk_type,
            }
            for h in hits
        ]
        return Response(
            {"hits": KBSearchHitSerializer(payload, many=True).data}
        )


class ConversationListView(generics.ListAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)


class ConversationDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)


class SemanticMemoryListView(generics.ListCreateAPIView):
    serializer_class = SemanticMemorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SemanticMemory.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SemanticMemoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SemanticMemorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SemanticMemory.objects.filter(user=self.request.user)


class MessageFeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = MessageFeedbackSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        payload = request.data
        message = get_object_or_404(
            Message,
            pk=payload["message"],
            conversation__user=request.user,
        )
        feedback, _ = MessageFeedback.objects.update_or_create(
            message=message,
            defaults={
                "user": request.user,
                "rating": payload["rating"],
                "comment": payload.get("comment", "") or "",
                "categories": payload.get("categories", []) or [],
            },
        )
        return Response(MessageFeedbackSerializer(feedback).data)
