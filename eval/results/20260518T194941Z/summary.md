# Eval results

- generated: 2026-05-18T19:51:01.408423+00:00
- questions: 25
- top_k: 12
- chat: on
- retrieval: none
- model: qwen3.5:9b
- reranker: off

## Overall

| metric | value |
|---|---|
| retrieval hit@12 (non-negative) | 0.00% |
| retrieval recall (non-negative) | 0.00% |
| answer keyword hit | 36.36% (n=22) |
| answer cites a doc | 18.18% |
| negatives abstained correctly | 100.00% (3/3) |
| retrieval p50 / p95 (ms) | 0 / 0 |
| chat p50 / p95 (ms) | 1641 / 8073 |

## By category

| category | n | hit@k | recall | kw hit | cites | abstain ok |
|---|---|---|---|---|---|---|
| single_hop | 8 | 0% | 0% | 12% | 25% | - |
| multi_hop | 6 | 0% | 0% | 17% | 17% | - |
| detail_tech | 5 | 0% | 0% | 80% | 20% | - |
| synthesis | 3 | 0% | 0% | 67% | 0% | - |
| negative | 3 | 0% | 0% | - | 0% | 100% |

## Per question

| id | cat | hit | recall | kw | cite | abstain |
|---|---|---|---|---|---|---|
| sh-01 | single_hop | N | 0% | N | N | - |
| sh-02 | single_hop | N | 0% | N | Y | - |
| sh-03 | single_hop | N | 0% | N | N | - |
| sh-04 | single_hop | N | 0% | N | Y | - |
| sh-05 | single_hop | N | 0% | Y | N | - |
| sh-06 | single_hop | N | 0% | N | N | - |
| sh-07 | single_hop | N | 0% | N | N | - |
| sh-08 | single_hop | N | 0% | N | N | - |
| mh-01 | multi_hop | N | 0% | N | N | - |
| mh-02 | multi_hop | N | 0% | N | N | - |
| mh-03 | multi_hop | N | 0% | N | N | - |
| mh-04 | multi_hop | N | 0% | Y | N | - |
| mh-05 | multi_hop | N | 0% | N | Y | - |
| mh-06 | multi_hop | N | 0% | N | N | - |
| dt-01 | detail_tech | N | 0% | N | N | - |
| dt-02 | detail_tech | N | 0% | Y | N | - |
| dt-03 | detail_tech | N | 0% | Y | N | - |
| dt-04 | detail_tech | N | 0% | Y | N | - |
| dt-05 | detail_tech | N | 0% | Y | Y | - |
| syn-01 | synthesis | N | 0% | Y | N | - |
| syn-02 | synthesis | N | 0% | N | N | - |
| syn-03 | synthesis | N | 0% | Y | N | - |
| neg-01 | negative | N | 0% | - | N | Y |
| neg-02 | negative | N | 0% | - | N | Y |
| neg-03 | negative | N | 0% | - | N | Y |
