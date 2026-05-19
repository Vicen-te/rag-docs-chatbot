from django.urls import path

from rag.views import (
    ChatView,
    ConversationDetailView,
    ConversationListView,
    KBSearchView,
    MessageFeedbackView,
    SemanticMemoryDetailView,
    SemanticMemoryListView,
)

urlpatterns = [
    path("chat/", ChatView.as_view(), name="chat"),
    path("kb/search/", KBSearchView.as_view(), name="kb-search"),
    path("memory/semantic/", SemanticMemoryListView.as_view(), name="memory-list"),
    path(
        "memory/semantic/<uuid:pk>/",
        SemanticMemoryDetailView.as_view(),
        name="memory-detail",
    ),
    path("conversations/", ConversationListView.as_view(), name="conversations"),
    path(
        "conversations/<uuid:pk>/",
        ConversationDetailView.as_view(),
        name="conversation-detail",
    ),
    path("feedback/", MessageFeedbackView.as_view(), name="feedback"),
]
