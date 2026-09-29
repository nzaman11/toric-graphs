# Conjectures log

Each entry: statement, supporting data, status, and proof notes. "Evidence" counts refer to
connected, non-bipartite, leaf-free graphs; "failing" means failing the odd cycle condition (OCC).

---

## C1. Gorenstein ⇔ complete intersection for graphs failing OCC

**Statement.** If G fails OCC and k[G] is Cohen–Macaulay, then k[G] is Gorenstein if and only if
I_G is a complete intersection (μ(I_G) = m − n).

**Evidence (n = 8, 2026-09-29).** 51 CM failing graphs. Exactly 3 have a symmetric h-vector
(graphs 1979, 2305, 5222) and exactly those 3 have μ(I_G) = m − n:

| graph | m | gens (degrees) | h-vector |
|---|---|---|---|
| 1979 | 9 | 1 (6) | (1,1,1,1,1,1) |
| 2305 | 10 | 2 (2,5) | (1,2,2,2,2,1) |
| 5222 | 11 | 3 (2,2,4) | (1,3,4,4,3,1) |

The ⇐ direction is a theorem (CI ⇒ Gorenstein). The data direction ⇒ is rigorous at n = 8:
non-symmetric h ⇒ not Gorenstein (Stanley) ⇒ not CI.

**Status.** Open. Test at n = 9. Literature: Gitler–Reyes–Villarreal and Tatakis–Thoma on
complete intersection toric ideals of graphs.

**Proof notes.** _(Navila)_

---

## C2. Non-CM failing graphs have a negative top h-coefficient

**Statement.** If G fails OCC and k[G] is not Cohen–Macaulay, then the numerator of the reduced
Hilbert series has a negative leading coefficient (and all other coefficients nonnegative).

**Evidence (n = 8, 2026-09-29).** All 110 non-CM graphs: every lower coefficient ≥ 0 and the top
coefficient is −1 (107 graphs) or −2 (3 graphs). All 110 have depth = n − 1.

Note: a negative h-coefficient ⇒ not CM is automatic (CM ⇒ h ≥ 0). The content is the converse:
at n = 8, non-CM is *always detected* by the Hilbert series, so CM could be decided from the
Hilbert series alone (much cheaper than a resolution).

**Status.** Open. Test at n = 9. Also: why depth exactly n − 1?

**Proof notes.** _(Navila)_

---

## C3. A separated pair inside one block forces non-CM

**Statement.** If G has two vertex-disjoint, non-adjacent chordless odd cycles C, C' lying in the
same 2-connected block (equivalently here: joined by 2 internally disjoint paths), then k[G] is
not Cohen–Macaulay.

**Evidence (n = 8, 2026-09-29).** Among the 161 failing graphs, 92 have such a pair and all 92
are non-CM. The other 69 (every separated pair linked only through a cut vertex) split 51 CM /
18 non-CM.

Related: 1 separated pair → 107 non-CM / 16 CM; ≥ 2 separated pairs → 3 non-CM / 35 CM.

**Status.** Open, first look only (univariate crosstabs, no model yet). Next: what separates the
51 CM from the 18 non-CM among the cut-vertex-linked graphs? Test at n = 9.

**Proof notes.** _(Navila)_

---

## C4. CM ⇔ no even cycle meets a separated pair (refines C3)

**Statement.** Let G fail OCC. Then k[G] is Cohen–Macaulay if and only if there is no even cycle
that shares a vertex with both cycles of some separated pair (C, C') (vertex-disjoint chordless odd
cycles with no edge between them).

**Evidence (2026-09-29).** Exact on all 167 failing graphs with n ≤ 8:

| | CM | not CM |
|---|---|---|
| no even cycle meets a separated pair | 57 (n=7: 6, n=8: 51) | 0 |
| some even cycle meets a separated pair | 0 | 110 |

C3 is the special case where C, C' lie in one block (then two disjoint C–C' paths plus arcs of C
and C' form such an even cycle).

**How it was found.** A depth-1 decision tree on the 161 n = 8 failing graphs split on
"has a 6-cycle" (108/108 not CM; 2 errors: graphs 89 and 2003). Asking *which* 6-cycles matter
led to the even-cycle-meets-pair criterion, which also fixes 89 and 2003. Because it was chosen
after looking at the n ≤ 8 data, **n = 9 is the real test** (see `reports/phase3_trees.txt`).

**Status. FALSE as stated (2026-09-29).** Predictions for all 7125 failing n = 9 graphs were
committed before any computation (commit `26f8783`). The first 48 graphs computed (all predicted
CM) include 3 counterexamples, each proved non-CM by a negative Hilbert coefficient:

| graph | edges (1-indexed) | separated pair | h-vector |
|---|---|---|---|
| 7161 | 15 18 28 48 58 26 69 37 39 49 79 | {1,5,8}, {3,7,9} | (1,2,3,4,3,1,−1) |
| 7758 | 15 18 58 26 29 69 37 47 78 39 49 | {1,5,8}, {2,6,9} | (1,2,2,2,2,2,−1) |
| 7921 | 15 18 58 26 29 69 37 47 38 78 39 49 | {1,5,8}, {2,6,9} | (1,3,5,6,4,1,−1) |

In each, the two triangles are joined only through cut vertices, but the connecting part contains
a cycle that C4 ignores: an **odd** cycle through both cut vertices (7161: pentagon 8-4-9-6-2), or
a cycle touching only **one** triangle (7758: bridge 8-7 then 4-cycle 7-3-9-4). At n = 8 there
are only 2 spare vertices, so any connecting cycle was forced to be even and to meet both
triangles — which is why C4 looked exact there.

Quick post-hoc refinements ("exactly one connecting path") did **not** fit the n ≤ 8 data;
refine only after the full n = 9 run.

**Intuition to probe:** a cycle in the "connector" between C and C' gives closed walks that mix
the two odd cycles, which might produce the extra relations that break CM. The right notion of
"connector" is the open question.

**Proof notes.** _(Navila)_

---

## Verified: Edge-threshold theorem (Navila, proved)

For connected G on n ≥ 7 vertices, failing OCC forces n + 1 ≤ m ≤ C(n,2) − 9, and every value
is attained. Verified computationally (with min degree ≥ 2) for n = 7, 8 in `tests/test_occ.py`.

## Observation: CM rate among failing graphs by edge count (n = 8)

| m | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| failing | 1 | 7 | 17 | 29 | 34 | 30 | 22 | 12 | 6 | 2 | 1 |
| CM | 1 | 4 | 10 | 13 | 12 | 7 | 3 | 1 | 0 | 0 | 0 |

No CM failing graph has m ≥ 17 at n = 8.
