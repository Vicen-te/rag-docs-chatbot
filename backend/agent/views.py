from __future__ import annotations

from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agent.kb.search import hybrid_search
from agent.models import Conversation, Message, SemanticMemory
from agent.orchestrator.graph import run_agent
from agent.orchestrator.streaming import sse_done, sse_error, sse_token
from agent.serializers import (
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
        conv_id = ser.validated_data.get("conversation_id")
        if conv_id:
            conversation = get_object_or_404(Conversation, id=conv_id, user=user)
        else:
            conversation = Conversation.objects.create(user=user)

        user_text = ser.validated_data["message"]
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content=user_text,
        )

        def stream():
            try:
                state = run_agent(user, conversation.id, user_text)
                final = state.get("final", "")
                for token in final.split(" "):
                    yield sse_token(token + " ")
                Message.objects.create(
                    conversation=conversation,
                    role=Message.Role.ASSISTANT,
                    content=final,
                )
                yield sse_done({"conversation_id": str(conversation.id)})
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


class MessageFeedbackView(generics.CreateAPIView):
    serializer_class = MessageFeedbackSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
