-- Toric ideal + reduced Hilbert series for a list of graphs in ONE session (no per-graph start-up).
-- Used for large runs (n = 10) where only the h-vector is needed for every graph and depth only
-- for the graphs whose h-vector is nonnegative.
--
--   M2 --script m2/compute_hilbert.m2 <input.m2> <output.txt> <numVertices>
-- <input.m2> defines graphList = { {graphNumber, "graph6", {{i,j},...}}, ... } (1-indexed edges).
-- Output: one tab-separated line per graph:
--   graphNumber  numGens  genDegrees  reducedHilbertSeries  cpuSeconds

args = drop(commandLine, position(commandLine, a -> match("compute_hilbert\\.m2$", a)) + 1);
load args#0;
out = openOut args#1;
nV = value args#2;
S = QQ[v_1..v_nV];
scan(graphList, g -> (
    (num, g6, E) := toSequence g;
    t0 := cpuTime();
    m := #E;
    R := QQ[e_1..e_m];
    I := trim ker map(S, R, apply(E, p -> v_(p#0) * v_(p#1)));
    hs := reduceHilbert hilbertSeries I;
    out << num << "\t" << numgens I << "\t" << toString sort flatten degrees I << "\t"
        << toString hs << "\t" << (cpuTime() - t0) << endl << flush;
    ));
close out;
exit 0;
