-- Compute toric ideal invariants for a list of graphs.
--
-- Usage (from the repo root):
--   M2 --script m2/compute_graphs.m2 <input.m2> <output.txt> <numVertices>
-- where <input.m2> defines   graphList = { {graphNumber, "graph6", {{i,j},...}}, ... };
-- with 1-indexed edges. Output is one "Key: value" block per graph, separated by "====".
--
-- Depth uses Auslander-Buchsbaum: depth(R/I) = numEdges - pdim(R/I), from a minimal
-- free resolution, so it is exact. R/I is CM iff depth = numVertices (non-bipartite, connected).

args = drop(commandLine, position(commandLine, a -> match("compute_graphs\\.m2$", a)) + 1);
if #args < 3 then error "usage: M2 --script m2/compute_graphs.m2 <input.m2> <output.txt> <numVertices>";
load args#0;
out = openOut args#1;
nV = value args#2;
S = QQ[v_1..v_nV];
scan(graphList, g -> (
    t0 := cpuTime();
    (num, g6, E) := toSequence g;
    m := #E;
    R := QQ[e_1..e_m];
    phi := map(S, R, apply(E, p -> v_(p#0) * v_(p#1)));
    I := trim ker phi;
    t1 := cpuTime();
    dep := m - pdim coker gens I;
    t2 := cpuTime();
    hs := reduceHilbert hilbertSeries I;
    t3 := cpuTime();
    out << "GraphNumber: " << num << endl
        << "Graph6: " << g6 << endl
        << "NumEdges: " << m << endl
        << "Edges: " << toString E << endl
        << "ToricIdeal: " << toString I << endl
        << "NumGens: " << numgens I << endl
        << "GenDegrees: " << toString sort flatten degrees I << endl
        << "Depth: " << dep << endl
        << "VerticesMinusDepth: " << nV - dep << endl
        << "ReducedHilbertSeries: " << toString hs << endl
        << "SecondsKer: " << (t1 - t0) << endl
        << "SecondsDepth: " << (t2 - t1) << endl
        << "SecondsHilbert: " << (t3 - t2) << endl
        << "========================" << endl << flush;
    ));
close out;
exit 0;
