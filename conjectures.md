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

## Verified: Edge-threshold theorem (Navila, proved)

For connected G on n ≥ 7 vertices, failing OCC forces n + 1 ≤ m ≤ C(n,2) − 9, and every value
is attained. Verified computationally (with min degree ≥ 2) for n = 7, 8 in `tests/test_occ.py`.

## Observation: CM rate among failing graphs by edge count (n = 8)

| m | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| failing | 1 | 7 | 17 | 29 | 34 | 30 | 22 | 12 | 6 | 2 | 1 |
| CM | 1 | 4 | 10 | 13 | 12 | 7 | 3 | 1 | 0 | 0 | 0 |

No CM failing graph has m ≥ 17 at n = 8.
