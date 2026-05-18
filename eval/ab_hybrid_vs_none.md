# Compare: 20260518T193827Z (hybrid) vs 20260518T194941Z (none)

- questions compared: 25

## Overall

| metric | A | B | delta |
|---|---|---|---|
| retrieval_hit | 100.00% | 0.00% | -100.0pp |
| retrieval_recall | 94.67% | 0.00% | -94.7pp |
| keyword_hit | 95.45% | 36.36% | -59.1pp |
| citation_present | 96.00% | 16.00% | -80.0pp |

## By category

| category | n | hit@k A->B | recall A->B | kw hit A->B |
|---|---|---|---|---|
| single_hop | 8 | 100% -> 0% (-100.0pp) | 100% -> 0% (-100.0pp) | 100% -> 12% (-87.5pp) |
| multi_hop | 6 | 100% -> 0% (-100.0pp) | 83% -> 0% (-83.3pp) | 83% -> 17% (-66.7pp) |
| detail_tech | 5 | 100% -> 0% (-100.0pp) | 100% -> 0% (-100.0pp) | 100% -> 80% (-20.0pp) |
| synthesis | 3 | 100% -> 0% (-100.0pp) | 89% -> 0% (-88.9pp) | 100% -> 67% (-33.3pp) |
| negative | 3 | 100% -> 0% (-100.0pp) | 100% -> 0% (-100.0pp) | - |

## Per question

| id | cat | hit A->B | recall A->B | kw A->B |
|---|---|---|---|---|
| dt-01 | detail_tech | Y -> N | 100% -> 0% | Y -> N |
| dt-02 | detail_tech | Y -> N | 100% -> 0% | Y -> Y |
| dt-03 | detail_tech | Y -> N | 100% -> 0% | Y -> Y |
| dt-04 | detail_tech | Y -> N | 100% -> 0% | Y -> Y |
| dt-05 | detail_tech | Y -> N | 100% -> 0% | Y -> Y |
| mh-01 | multi_hop | Y -> N | 100% -> 0% | Y -> N |
| mh-02 | multi_hop | Y -> N | 50% -> 0% | N -> N |
| mh-03 | multi_hop | Y -> N | 100% -> 0% | Y -> N |
| mh-04 | multi_hop | Y -> N | 100% -> 0% | Y -> Y |
| mh-05 | multi_hop | Y -> N | 100% -> 0% | Y -> N |
| mh-06 | multi_hop | Y -> N | 50% -> 0% | Y -> N |
| neg-01 | negative | Y -> N | 100% -> 0% | - -> - |
| neg-02 | negative | Y -> N | 100% -> 0% | - -> - |
| neg-03 | negative | Y -> N | 100% -> 0% | - -> - |
| sh-01 | single_hop | Y -> N | 100% -> 0% | Y -> N |
| sh-02 | single_hop | Y -> N | 100% -> 0% | Y -> N |
| sh-03 | single_hop | Y -> N | 100% -> 0% | Y -> N |
| sh-04 | single_hop | Y -> N | 100% -> 0% | Y -> N |
| sh-05 | single_hop | Y -> N | 100% -> 0% | Y -> Y |
| sh-06 | single_hop | Y -> N | 100% -> 0% | Y -> N |
| sh-07 | single_hop | Y -> N | 100% -> 0% | Y -> N |
| sh-08 | single_hop | Y -> N | 100% -> 0% | Y -> N |
| syn-01 | synthesis | Y -> N | 100% -> 0% | Y -> Y |
| syn-02 | synthesis | Y -> N | 67% -> 0% | Y -> N |
| syn-03 | synthesis | Y -> N | 100% -> 0% | Y -> Y |
