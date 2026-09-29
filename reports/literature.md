# Literature check (2026-09-29)

Scope: Cohen–Macaulayness of edge rings k[G] for graphs failing the odd cycle condition (OCC),
and the conjectures in `conjectures.md`. Web search + reading of the key papers; a first pass,
not an exhaustive survey — confirm with Prof. O'Keefe, who co-authored two of the central papers.

## Most relevant

**Hà, Kara, O'Keefe — "Algebraic properties of toric rings of graphs" (arXiv:1703.08270, 2017).**
- Thm 3.6: for an induced subgraph H of G, reg and pd of k[H] bound those of k[G]; and if
  |E_H| − |V_H| ≥ |E_G| − |V_G| and k[H] is not CM, then k[G] is not CM (via algebra retracts).
- **Thm 5.1:** if |E| ≤ |V| + 2 and G has an induced subgraph made of two vertex-disjoint odd
  cycles joined by two vertex-disjoint (except possibly at endpoints) paths of length ≥ 2, then
  k[G] is not CM.
- Intro: two odd cycles joined by a single path give a non-normal but CM ring (our graph 1979).
- Ex. 5.4 (due to K. Kimura): a 9-vertex, 12-edge graph (|E| = |V| + 3) that contains the
  forbidden structure but **is CM** — Thm 5.1 fails without |E| ≤ |V| + 2.
- Ex. 5.2/5.3: if the two paths share internal vertices, k[G] can be CM or not.

**Relation to our data.** Our C3 is Thm 5.1 without the edge bound. Its n = 9 counterexamples are
exactly what Ex. 5.4 predicts: no CM graph with a separated pair in one block has m − n ≤ 2 (at
n = 8 or 9); the first ones appear at m − n = 3 (exactly one graph at n = 9, plausibly Kimura's).
So C3's failure is **known**, and our data is **consistent** with Thm 5.1 (1 + 1 graphs with
m − n = 2 and a same-block pair, both non-CM).

**Hibi, Higashitani, Kimura, O'Keefe — "Depth of edge rings arising from finite graphs"
(Proc. AMS 139, 2011; arXiv:1009.1472).**
- For all 7 ≤ f ≤ d there is a graph on d vertices with depth k[G] = f and dim d (two triangles
  joined by paths, plus extra edges).
- **Conjecture 0.1:** depth k[G] ≥ 7 for every graph on d ≥ 7 vertices. Our n = 8 non-CM graphs
  all have depth 7 (consistent). Not yet tested at n = 9 (the runner skipped depth for non-CM
  graphs); depth over ZZ/32003 is a lower bound for depth over QQ, so a cheap ZZ/p run on the
  6,400 non-CM graphs could confirm it for n = 9.
- States that when an edge ring is CM is "presumably open" (as of 2011).

**Serre's conditions.** CM ⇒ (S₂), and normal ⇔ (R₁) + (S₂).
- Higashitani–Kimura (Adv. Stud. Pure Math. 77, 2018): a necessary condition for (S₂).
- Hibi–Katthän, "Edge rings satisfying Serre's condition R₁" (arXiv:1202.4889): combinatorial
  criterion for (R₁); for (R₁) edge rings, CM ⇔ normal ⇔ OCC.
- Shibu Deepthi, "Non-normal edge rings satisfying (S₂)" (arXiv:2207.01217) and Dinu–Shibu
  Deepthi, "(S₂)-condition of edge rings for cactus graphs" (arXiv:2402.17413, Comm. Algebra
  2025): families of non-normal edge rings with (S₂), using Katthän's criterion for non-normal
  affine semigroup rings.

**h-vectors of edge rings.** Recent work computes h-vectors for OCC (normal) families, e.g.
Bhaskara–Higashitani–Shibu Deepthi (arXiv:2311.13573) and pseudo/almost Gorenstein edge rings
(arXiv:2409.03176). These are normal cases, where h ≥ 0 automatically.

## Status of our conjectures against the literature

| | literature |
|---|---|
| C1 Gorenstein ⇔ CI | refuted by our data; CI toric ideals of graphs: Gitler–Reyes–Villarreal, Tatakis–Thoma (not re-read here) |
| C2′ CM ⇔ h ≥ 0 (failing G) | **no prior statement found.** CM ⇒ h ≥ 0 is classical; the converse is the new content |
| C3 same-block pair ⇒ not CM | **known with |E| ≤ |V| + 2** (Hà–Kara–O'Keefe Thm 5.1); known false without it (Kimura, Ex. 5.4) |
| C4 / C4′ | refuted by our data; closest known results are Thm 5.1 and Ex. 5.2–5.4 |
| Edge threshold theorem | not checked for prior statements; it is elementary (upper bound = two triangles with no edges between) |

## Suggested questions for Prof. O'Keefe

1. Is "CM ⇔ h-vector nonnegative" (C2′) known or expected for edge rings of graphs failing OCC,
   or for non-normal edge rings in general? Is there a structural reason (e.g. via the
   normalization, whose h-vector is nonnegative, and the Hilbert series of the "holes")?
2. Is Conjecture 0.1 (depth ≥ 7) still open? We can test it at n = 9 cheaply.
3. Can Thm 5.1's bound |E| ≤ |V| + 2 be replaced by a structural condition? Our 89 n = 9 graphs
   with a same-block pair that are CM (m − n = 3 … 12) are test cases.

## Sources

- https://arxiv.org/abs/1703.08270
- https://arxiv.org/abs/1009.1472 (ar5iv: https://ar5iv.labs.arxiv.org/html/1009.1472)
- https://arxiv.org/abs/1202.4889
- https://arxiv.org/abs/2207.01217
- https://arxiv.org/abs/2402.17413v3
- https://arxiv.org/abs/2311.13573
- https://arxiv.org/pdf/2409.03176
