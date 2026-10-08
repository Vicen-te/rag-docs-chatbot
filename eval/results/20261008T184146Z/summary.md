# Eval results

- generated: 2026-10-08T18:43:06.639663+00:00
- questions: 25
- top_k: 26
- chat: on
- retrieval: none
- model: qwen3.5:9b
- reranker: off
- query decomposition: off
- fusion weights: semantic 0.5 / lexical 0.5

## Overall

| metric | value |
|---|---|
| retrieval hit@26 (non-negative) | 0.00% |
| retrieval recall (non-negative) | 0.00% |
| answer keyword hit | 36.36% (n=22) |
| answer cites a doc | 54.55% |
| negatives abstained correctly | 100.00% (3/3) |
| retrieval p50 / p95 (ms) | 0 / 0 |
| chat p50 / p95 (ms) | 1673 / 6975 |

## By category

| category | n | hit@k | recall | kw hit | cites | abstain ok |
|---|---|---|---|---|---|---|
| single_hop | 8 | 0% | 0% | 12% | 38% | - |
| multi_hop | 6 | 0% | 0% | 33% | 67% | - |
| detail_tech | 5 | 0% | 0% | 60% | 40% | - |
| synthesis | 3 | 0% | 0% | 67% | 100% | - |
| negative | 3 | 0% | 0% | - | 0% | 100% |

## Per question

| id | cat | hit | recall | kw | cite | abstain |
|---|---|---|---|---|---|---|
| sh-01 | single_hop | N | 0% | N | N | - |
| sh-02 | single_hop | N | 0% | N | Y | - |
| sh-03 | single_hop | N | 0% | N | N | - |
| sh-04 | single_hop | N | 0% | N | Y | - |
| sh-05 | single_hop | N | 0% | Y | N | - |
| sh-06 | single_hop | N | 0% | N | Y | - |
| sh-07 | single_hop | N | 0% | N | N | - |
| sh-08 | single_hop | N | 0% | N | N | - |
| mh-01 | multi_hop | N | 0% | N | N | - |
| mh-02 | multi_hop | N | 0% | N | Y | - |
| mh-03 | multi_hop | N | 0% | N | Y | - |
| mh-04 | multi_hop | N | 0% | Y | N | - |
| mh-05 | multi_hop | N | 0% | N | Y | - |
| mh-06 | multi_hop | N | 0% | Y | Y | - |
| dt-01 | detail_tech | N | 0% | N | N | - |
| dt-02 | detail_tech | N | 0% | Y | Y | - |
| dt-03 | detail_tech | N | 0% | Y | N | - |
| dt-04 | detail_tech | N | 0% | N | Y | - |
| dt-05 | detail_tech | N | 0% | Y | N | - |
| syn-01 | synthesis | N | 0% | Y | Y | - |
| syn-02 | synthesis | N | 0% | N | Y | - |
| syn-03 | synthesis | N | 0% | Y | Y | - |
| neg-01 | negative | N | 0% | - | N | Y |
| neg-02 | negative | N | 0% | - | N | Y |
| neg-03 | negative | N | 0% | - | N | Y |
