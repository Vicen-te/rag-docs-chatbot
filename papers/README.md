# Corpus: 13 foundational AI papers

Drop the PDFs below into this directory with the **exact filenames** listed.
Then ingest with:

```bash
cd backend
python manage.py ingest_papers ../papers/
```

| # | Filename            | Title                                                                       | arXiv |
|---|---------------------|-----------------------------------------------------------------------------|------|
| 1 | `attention.pdf`     | Attention Is All You Need (Vaswani et al., 2017)                            | [1706.03762](https://arxiv.org/pdf/1706.03762) |
| 2 | `sbert.pdf`         | Sentence-BERT (Reimers & Gurevych, 2019)                                    | [1908.10084](https://arxiv.org/pdf/1908.10084) |
| 3 | `qwen3.pdf`         | Qwen3 Technical Report (Qwen Team, 2025)                                    | [2505.09388](https://arxiv.org/pdf/2505.09388) |
| 4 | `hyde.pdf`          | Precise Zero-Shot Dense Retrieval without Relevance Labels (Gao et al., 2022) | [2212.10496](https://arxiv.org/pdf/2212.10496) |
| 5 | `self-rag.pdf`      | Self-RAG: Learning to Retrieve, Generate, and Critique (Asai et al., 2023)  | [2310.11511](https://arxiv.org/pdf/2310.11511) |
| 6 | `react.pdf`         | ReAct: Synergizing Reasoning and Acting (Yao et al., 2022)                  | [2210.03629](https://arxiv.org/pdf/2210.03629) |
| 7 | `reflexion.pdf`     | Reflexion: Language Agents with Verbal RL (Shinn et al., 2023)              | [2303.11366](https://arxiv.org/pdf/2303.11366) |
| 8 | `lora.pdf`          | LoRA: Low-Rank Adaptation (Hu et al., 2021)                                 | [2106.09685](https://arxiv.org/pdf/2106.09685) |
| 9 | `qlora.pdf`         | QLoRA: Efficient Finetuning of Quantized LLMs (Dettmers et al., 2023)       | [2305.14314](https://arxiv.org/pdf/2305.14314) |
| 10 | `vllm.pdf`         | PagedAttention / vLLM (Kwon et al., 2023)                                   | [2309.06180](https://arxiv.org/pdf/2309.06180) |
| 11 | `vit.pdf`          | An Image is Worth 16x16 Words (Dosovitskiy et al., 2020)                    | [2010.11929](https://arxiv.org/pdf/2010.11929) |
| 12 | `sam2.pdf`         | SAM 2: Segment Anything in Images and Videos (Ravi et al., 2024)            | [2408.00714](https://arxiv.org/pdf/2408.00714) |
| 13 | `ragas.pdf`        | Ragas: Automated Evaluation of RAG (Es et al., 2023)                        | [2309.15217](https://arxiv.org/pdf/2309.15217) |

The PDF filenames are referenced verbatim by `eval/dataset.jsonl` (the
`expected_source` field), so do not rename them.
