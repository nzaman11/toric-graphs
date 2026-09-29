-- Re-measure Macaulay2 CPU time of the depth stage (over ZZ/32003) for a list of graphs, in ONE
-- session so start-up is not counted. Used to cost the n = 9 run fairly (scripts/analyze_n9.py).
--
--   M2 --script m2/time_depth.m2 <input.m2> <output.txt> <numVertices>
-- <input.m2> defines graphList = { {graphNumber, "graph6", {{i,j},...}}, ... } (1-indexed edges).
-- Output: one line per graph "graphNumber depth seconds".

args = drop(commandLine, position(commandLine, a -> match("time_depth\\.m2$", a)) + 1);
load args#0;
out = openOut args#1;
nV = value args#2;
kk = ZZ/32003;
S = kk[v_1..v_nV];
scan(graphList, g -> (
    (num, g6, E) := toSequence g;
    m := #E;
    R := kk[e_1..e_m];
    I := trim ker map(S, R, apply(E, p -> v_(p#0) * v_(p#1)));
    t0 := cpuTime();
    dep := m - pdim coker gens I;
    out << num << " " << dep << " " << (cpuTime() - t0) << endl << flush;
    ));
close out;
exit 0;
