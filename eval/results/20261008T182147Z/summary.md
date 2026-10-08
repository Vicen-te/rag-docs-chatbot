# Eval results

- generated: 2026-10-08T18:21:49.868286+00:00
- questions: 25
- top_k: 26
- chat: off
- retrieval: hybrid
- model: qwen3.5:9b
- reranker: off
- query decomposition: off
- fusion weights: semantic 0.5 / lexical 0.5

## Overall

| metric | value |
|---|---|
| retrieval hit@26 (non-negative) | 100.00% |
| retrieval recall (non-negative) | 98.48% |

## By category

| category | n | hit@k | recall | 
|---|---|---|---|
| single_hop | 8 | 100% | 100% | 
| multi_hop | 6 | 100% | 100% | 
| detail_tech | 5 | 100% | 100% | 
| synthesis | 3 | 100% | 89% | 
| negative | 3 | 100% | 100% | 

## Per question

| id | cat | hit | recall | kw | cite | abstain |
|---|---|---|---|---|---|---|
| sh-01 | single_hop | Y | 100% | - | N | - |
| sh-02 | single_hop | Y | 100% | - | N | - |
| sh-03 | single_hop | Y | 100% | - | N | - |
| sh-04 | single_hop | Y | 100% | - | N | - |
| sh-05 | single_hop | Y | 100% | - | N | - |
| sh-06 | single_hop | Y | 100% | - | N | - |
| sh-07 | single_hop | Y | 100% | - | N | - |
| sh-08 | single_hop | Y | 100% | - | N | - |
| mh-01 | multi_hop | Y | 100% | - | N | - |
| mh-02 | multi_hop | Y | 100% | - | N | - |
| mh-03 | multi_hop | Y | 100% | - | N | - |
| mh-04 | multi_hop | Y | 100% | - | N | - |
| mh-05 | multi_hop | Y | 100% | - | N | - |
| mh-06 | multi_hop | Y | 100% | - | N | - |
| dt-01 | detail_tech | Y | 100% | - | N | - |
| dt-02 | detail_tech | Y | 100% | - | N | - |
| dt-03 | detail_tech | Y | 100% | - | N | - |
| dt-04 | detail_tech | Y | 100% | - | N | - |
| dt-05 | detail_tech | Y | 100% | - | N | - |
| syn-01 | synthesis | Y | 100% | - | N | - |
| syn-02 | synthesis | Y | 67% | - | N | - |
| syn-03 | synthesis | Y | 100% | - | N | - |
| neg-01 | negative | Y | 100% | - | N | N |
| neg-02 | negative | Y | 100% | - | N | N |
| neg-03 | negative | Y | 100% | - | N | N |
