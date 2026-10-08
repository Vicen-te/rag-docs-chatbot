"""Unit tests for the retrieval pieces that need neither the LLM nor
a database: the lexical query builder and the RRF fusion."""
from django.test import SimpleTestCase, override_settings

from rag.kb.search import SearchHit, _reciprocal_rank_fusion, lexical_query


def _hit(chunk_id: str, doc: str = "d") -> SearchHit:
    return SearchHit(
        chunk_id=chunk_id,
        document_id=doc,
        document_name=f"{doc}.pdf",
        content="",
        score=0.0,
        parent_id=None,
        chunk_type="child",
    )


class LexicalQueryTests(SimpleTestCase):
    def test_terms_are_or_joined_and_lowercased(self):
        q = lexical_query("What does QLoRA add on top of LoRA?")
        self.assertEqual(q, "what or does or qlora or add or on or top or of or lora")

    def test_punctuation_is_stripped_and_identifiers_survive(self):
        q = lexical_query("In 'Attention Is All You Need', why d_k (ViT-B/16)?")
        self.assertEqual(
            q, "in or attention or is or all or you or need or why or d_k or vit-b or 16",
        )

    def test_repeated_terms_appear_once(self):
        self.assertEqual(lexical_query("block block Block"), "block")

    def test_empty_question_gives_empty_query(self):
        self.assertEqual(lexical_query("?!"), "")


@override_settings(KB_RRF_K=60, KB_SEMANTIC_WEIGHT=0.7, KB_LEXICAL_WEIGHT=0.3)
class ReciprocalRankFusionTests(SimpleTestCase):
    def test_chunk_in_both_channels_outranks_single_channel_leaders(self):
        sem = [_hit("a"), _hit("b"), _hit("c")]
        lex = [_hit("c"), _hit("d")]
        fused = _reciprocal_rank_fusion([sem, lex], top_k=4)
        self.assertEqual([h.chunk_id for h in fused], ["c", "a", "b", "d"])
        self.assertAlmostEqual(fused[0].score, 0.7 / 63 + 0.3 / 61)

    def test_top_k_truncates(self):
        sem = [_hit(str(i)) for i in range(10)]
        fused = _reciprocal_rank_fusion([sem, []], top_k=3)
        self.assertEqual([h.chunk_id for h in fused], ["0", "1", "2"])

    def test_empty_lexical_channel_reduces_to_semantic_order(self):
        sem = [_hit("x"), _hit("y")]
        fused = _reciprocal_rank_fusion([sem, []], top_k=2)
        self.assertEqual([h.chunk_id for h in fused], ["x", "y"])

    @override_settings(KB_SEMANTIC_WEIGHT=0.0, KB_LEXICAL_WEIGHT=1.0)
    def test_weights_pick_the_channel(self):
        sem = [_hit("a"), _hit("b")]
        lex = [_hit("b"), _hit("a")]
        fused = _reciprocal_rank_fusion([sem, lex], top_k=2)
        self.assertEqual([h.chunk_id for h in fused], ["b", "a"])
