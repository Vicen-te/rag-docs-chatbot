# Compare: 20261008T182441Z (hybrid) vs 20261008T183555Z (lexical)

- questions compared: 25

## Overall

| metric | A | B | delta |
|---|---|---|---|
| retrieval_hit | 100.00% | 100.00% | +0.0pp |
| retrieval_recall | 98.67% | 96.00% | -2.7pp |
| keyword_hit | 90.91% | 90.91% | +0.0pp |
| citation_present | 100.00% | 100.00% | +0.0pp |

## By category

| category | n | hit@k A->B | recall A->B | kw hit A->B |
|---|---|---|---|---|
| single_hop | 8 | 100% -> 100% (+0.0pp) | 100% -> 100% (+0.0pp) | 88% -> 100% (+12.5pp) |
| multi_hop | 6 | 100% -> 100% (+0.0pp) | 100% -> 92% (-8.3pp) | 83% -> 83% (+0.0pp) |
| detail_tech | 5 | 100% -> 100% (+0.0pp) | 100% -> 100% (+0.0pp) | 100% -> 80% (-20.0pp) |
| synthesis | 3 | 100% -> 100% (+0.0pp) | 89% -> 83% (-5.6pp) | 100% -> 100% (+0.0pp) |
| negative | 3 | 100% -> 100% (+0.0pp) | 100% -> 100% (+0.0pp) | - |

## Per question

| id | cat | hit A->B | recall A->B | kw A->B |
|---|---|---|---|---|
| dt-01 | detail_tech | Y -> Y | 100% -> 100% | Y -> N |
| dt-02 | detail_tech | Y -> Y | 100% -> 100% | Y -> Y |
| dt-03 | detail_tech | Y -> Y | 100% -> 100% | Y -> Y |
| dt-04 | detail_tech | Y -> Y | 100% -> 100% | Y -> Y |
| dt-05 | detail_tech | Y -> Y | 100% -> 100% | Y -> Y |
| mh-01 | multi_hop | Y -> Y | 100% -> 100% | Y -> Y |
| mh-02 | multi_hop | Y -> Y | 100% -> 100% | N -> Y |
| mh-03 | multi_hop | Y -> Y | 100% -> 100% | Y -> Y |
| mh-04 | multi_hop | Y -> Y | 100% -> 100% | Y -> Y |
| mh-05 | multi_hop | Y -> Y | 100% -> 50% | Y -> N |
| mh-06 | multi_hop | Y -> Y | 100% -> 100% | Y -> Y |
| neg-01 | negative | Y -> Y | 100% -> 100% | - -> - |
| neg-02 | negative | Y -> Y | 100% -> 100% | - -> - |
| neg-03 | negative | Y -> Y | 100% -> 100% | - -> - |
| sh-01 | single_hop | Y -> Y | 100% -> 100% | Y -> Y |
| sh-02 | single_hop | Y -> Y | 100% -> 100% | Y -> Y |
| sh-03 | single_hop | Y -> Y | 100% -> 100% | Y -> Y |
| sh-04 | single_hop | Y -> Y | 100% -> 100% | Y -> Y |
| sh-05 | single_hop | Y -> Y | 100% -> 100% | Y -> Y |
| sh-06 | single_hop | Y -> Y | 100% -> 100% | N -> Y |
| sh-07 | single_hop | Y -> Y | 100% -> 100% | Y -> Y |
| sh-08 | single_hop | Y -> Y | 100% -> 100% | Y -> Y |
| syn-01 | synthesis | Y -> Y | 100% -> 50% | Y -> Y |
| syn-02 | synthesis | Y -> Y | 67% -> 100% | Y -> Y |
| syn-03 | synthesis | Y -> Y | 100% -> 100% | Y -> Y |
