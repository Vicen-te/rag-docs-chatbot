# Eval results

- generated: 2026-10-08T18:35:48.978763+00:00
- questions: 25
- top_k: 26
- chat: on
- retrieval: semantic
- model: qwen3.5:9b
- reranker: off
- query decomposition: off
- fusion weights: semantic 0.5 / lexical 0.5

## Overall

| metric | value |
|---|---|
| retrieval hit@26 (non-negative) | 100.00% |
| retrieval recall (non-negative) | 96.21% |
| answer keyword hit | 95.45% (n=22) |
| answer cites a doc | 100.00% |
| negatives abstained correctly | 66.67% (2/3) |
| retrieval p50 / p95 (ms) | 65 / 70 |
| chat p50 / p95 (ms) | 15149 / 19596 |

## By category

| category | n | hit@k | recall | kw hit | cites | abstain ok |
|---|---|---|---|---|---|---|
| single_hop | 8 | 100% | 100% | 100% | 100% | - |
| multi_hop | 6 | 100% | 92% | 83% | 100% | - |
| detail_tech | 5 | 100% | 100% | 100% | 100% | - |
| synthesis | 3 | 100% | 89% | 100% | 100% | - |
| negative | 3 | 100% | 100% | - | 100% | 67% |

## Per question

| id | cat | hit | recall | kw | cite | abstain |
|---|---|---|---|---|---|---|
| sh-01 | single_hop | Y | 100% | Y | Y | - |
| sh-02 | single_hop | Y | 100% | Y | Y | - |
| sh-03 | single_hop | Y | 100% | Y | Y | - |
| sh-04 | single_hop | Y | 100% | Y | Y | - |
| sh-05 | single_hop | Y | 100% | Y | Y | - |
| sh-06 | single_hop | Y | 100% | Y | Y | - |
| sh-07 | single_hop | Y | 100% | Y | Y | - |
| sh-08 | single_hop | Y | 100% | Y | Y | - |
| mh-01 | multi_hop | Y | 100% | Y | Y | - |
| mh-02 | multi_hop | Y | 100% | N | Y | - |
| mh-03 | multi_hop | Y | 100% | Y | Y | - |
| mh-04 | multi_hop | Y | 100% | Y | Y | - |
| mh-05 | multi_hop | Y | 100% | Y | Y | - |
| mh-06 | multi_hop | Y | 50% | Y | Y | - |
| dt-01 | detail_tech | Y | 100% | Y | Y | - |
| dt-02 | detail_tech | Y | 100% | Y | Y | - |
| dt-03 | detail_tech | Y | 100% | Y | Y | - |
| dt-04 | detail_tech | Y | 100% | Y | Y | - |
| dt-05 | detail_tech | Y | 100% | Y | Y | - |
| syn-01 | synthesis | Y | 100% | Y | Y | - |
| syn-02 | synthesis | Y | 67% | Y | Y | - |
| syn-03 | synthesis | Y | 100% | Y | Y | - |
| neg-01 | negative | Y | 100% | - | Y | N |
| neg-02 | negative | Y | 100% | - | Y | Y |
| neg-03 | negative | Y | 100% | - | Y | Y |
