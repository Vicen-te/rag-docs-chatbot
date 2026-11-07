"""Unit tests for the pre-graph router: keywords must match whole words,
not fragments of longer words."""
from django.test import SimpleTestCase

from rag.orchestrator.router import classify_task_type, try_fast_route


class ClassifyTaskTypeTests(SimpleTestCase):
    def test_bare_greetings_are_conversational(self):
        for msg in ("hi", "Hello", "HEY", "thanks", "bye", "Thank you"):
            self.assertEqual(classify_task_type(msg), "conversational", msg)

    def test_greeting_with_short_tail_is_conversational(self):
        self.assertEqual(classify_task_type("hi there"), "conversational")
        self.assertEqual(classify_task_type("Hello, who are you?"), "conversational")
        self.assertEqual(classify_task_type("what can you do?"), "conversational")

    def test_hi_inside_a_word_is_not_a_greeting(self):
        self.assertEqual(classify_task_type("Explain the ViT architecture"), "rag")
        self.assertEqual(classify_task_type("What is this"), "rag")
        self.assertEqual(classify_task_type("which chip"), "rag")

    def test_other_keywords_inside_a_word_are_not_greetings(self):
        self.assertEqual(classify_task_type("They"), "rag")  # "hey"
        self.assertEqual(classify_task_type("Whey protein"), "rag")  # "hey"
        self.assertEqual(classify_task_type("Thanksgiving"), "rag")  # "thanks"
        self.assertEqual(classify_task_type("Goodbyes"), "rag")  # "goodbye"
        self.assertEqual(classify_task_type("Hello1"), "rag")

    def test_long_messages_go_to_rag_even_with_a_greeting(self):
        msg = "hi can you explain how multi head attention works in the transformer"
        self.assertEqual(classify_task_type(msg), "rag")

    def test_ordinary_question_goes_to_rag(self):
        self.assertEqual(classify_task_type("What does QLoRA add on top of LoRA?"), "rag")


class TryFastRouteTests(SimpleTestCase):
    def test_exact_greetings_get_a_canned_reply(self):
        self.assertEqual(try_fast_route("hi"), "Hello! How can I help you today?")
        self.assertEqual(try_fast_route(" Thank you "), "You're welcome.")

    def test_greeting_with_tail_or_embedded_word_gets_none(self):
        self.assertIsNone(try_fast_route("hi there"))
        self.assertIsNone(try_fast_route("Explain the ViT architecture"))
