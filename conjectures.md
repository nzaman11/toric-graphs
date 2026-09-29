# Conjectures log

Each entry: statement, supporting data, status, and proof notes. "Evidence" counts refer to
connected, non-bipartite, leaf-free graphs; "failing" means failing the odd cycle condition (OCC).

**Scope.** All CM / Gorenstein statements are over k = ℚ (Macaulay2 computations over QQ, or over
ZZ/32003 where depth = n, which implies depth = n over QQ for toric rings). For non-normal affine
semigroup rings, Cohen–Macaulayness can depend on the characteristic (Trung–Hoa), so nothing here
is claimed for other fields.

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

The ⇐ direction is a theorem (CI ⇒ Gorenstein). The ⇒ direction holds at n = 8 because
Gorenstein ⇒ symmetric h (Stanley), which singles out exactly graphs 1979, 2305, 5222, and each
of those has μ(I_G) = m − n.

**Status. FALSE at n = 9 (2026-09-29).** First found in the partial run (first 162 CM graphs:
13 Gorenstein, 9 CI, 4 not CI); final counts are in `reports/n9_results.md`. Examples:

| graph | m | codim | minimal gens (degrees) | h-vector |
|---|---|---|---|---|
| 8866 | 12 | 3 | 5 (2,2,2,5,5) | (1,3,3,3,3,1) |
| 19757 | 12 | 3 | 5 (2,2,2,5,5) | (1,3,3,3,3,1) |
| 10185 | 13 | 4 | 9 (2,2,2,2,2,2,5,5,5) | (1,4,4,4,4,1) |
| 24276 | 13 | 4 | 6 (2,2,2,2,2,4) | (1,4,5,5,4,1) |

Rigorous given Macaulay2: CM from exact depth, Gorenstein by Stanley, generator counts
from `trim` (minimal for homogeneous ideals). Consistency check: the codim-3 examples have
5 generators, as Buchsbaum–Eisenbud requires (codim-3 Gorenstein, not CI ⇒ an odd number
≥ 5 of generators, the Pfaffians of a skew matrix). Still true: CI ⇒ Gorenstein (theorem), and
at n = 8 the two classes coincide. New question: which structure gives the Pfaffian-type
Gorenstein graphs? Literature: Gitler–Reyes–Villarreal and Tatakis–Thoma on complete
intersection toric ideals of graphs.

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
same 2-connected block (equivalently, by Menger: joined by 2 vertex-disjoint C–C′ paths), then
k[G] is not Cohen–Macaulay.

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

C3 follows from the "⇐ not CM" half of C4 (C4′ below): if C, C′ lie in one block, take two
vertex-disjoint *shortest* C–C′ paths (so they avoid C ∪ C′ internally); together with an arc of
C and an arc of C′ between their endpoints they form a cycle meeting both. The two arcs of an odd
cycle between two vertices have opposite parity, so the arc of C can be chosen to make that cycle
even.

**C4′ (the half that is not refuted).** If some even cycle meets both cycles of a separated
pair, then k[G] is not CM. The n = 9 counterexamples below all go the *other* way (predicted CM,
actually not CM), so C4′ is still open; its n = 9 test is in `reports/n9_results.md`.

**How it was found.** A depth-1 decision tree on the 161 n = 8 failing graphs split on
"has a 6-cycle" (108/108 not CM; 2 errors: graphs 89 and 2003). Asking *which* 6-cycles matter
led to the even-cycle-meets-pair criterion, which also fixes 89 and 2003. Because it was chosen
after looking at the n ≤ 8 data, **n = 9 is the real test** (see `reports/phase3_trees.txt`).

**Status. FALSE as stated (2026-09-29).** Predictions for all 7125 failing n = 9 graphs were
committed before any computation (commit `26f8783`); raw results were committed before any
scoring (commit `fb90de6`). The first 48 graphs computed (all predicted CM) already included
3 counterexamples, each proved non-CM by a negative Hilbert coefficient (full list in
`reports/n9_results.md`):

| graph | edges (1-indexed) | separated pair | h-vector |
|---|---|---|---|
| 7161 | 15 18 28 48 58 26 69 37 39 49 79 | {1,5,8}, {3,7,9} | (1,2,3,4,3,1,−1) |
| 7758 | 15 18 58 26 29 69 37 47 78 39 49 | {1,5,8}, {2,6,9} | (1,2,2,2,2,2,−1) |
| 7921 | 15 18 58 26 29 69 37 47 38 78 39 49 | {1,5,8}, {2,6,9} | (1,3,5,6,4,1,−1) |

In each, the two triangles are joined only through cut vertices, but the connecting part contains
a cycle that C4 ignores: an **odd** cycle through both cut vertices (7161: pentagon 8-4-9-6-2), or
a cycle touching only **one** triangle (7758: bridge 8-7 then 4-cycle 7-3-9-4).

*Correction (independent review):* an earlier version said that at n = 8 any connecting cycle is
forced to be even and to meet both triangles. That is false — e.g. triangles A, B plus vertex 7
adjacent to a₁, b₁ and vertex 8 adjacent to 7, b₁ gives a failing n = 8 graph whose connector
contains the odd triangle {7, 8, b₁}, touching only B (and C4 still predicts it correctly). So
"a cycle in the connector ⇒ not CM" is not the rule either; the counterexamples need a finer
description.

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
