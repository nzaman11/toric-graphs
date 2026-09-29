-- One graph, one stage. Called by src/toric_graphs/runner.py.
--
--   M2 --script m2/compute_one.m2 "<edges>" <numVertices> ideal
--       toric ideal (trimmed), generator degrees, reduced Hilbert series
--   M2 --script m2/compute_one.m2 "<edges>" <numVertices> depth <QQ|ZZp>
--       depth(R/I) = numEdges - pdim(R/I), over QQ or ZZ/32003
--
-- <edges> is a Macaulay2 list like {{1,4},{2,5},...} (1-indexed). Output: "Key: value" lines.

args = drop(commandLine, position(commandLine, a -> match("compute_one\\.m2$", a)) + 1);
E = value args#0;
nV = value args#1;
mode = args#2;
kk = if mode == "depth" and args#3 == "ZZp" then ZZ/32003 else QQ;
m = #E;
S = kk[v_1..v_nV];
R = kk[e_1..e_m];
t0 = cpuTime();
I = trim ker map(S, R, apply(E, p -> v_(p#0) * v_(p#1)));
t1 = cpuTime();
if mode == "ideal" then (
    hs = reduceHilbert hilbertSeries I;
    t2 = cpuTime();
    print("ToricIdeal: " | toString I);
    print("NumGens: " | toString numgens I);
    print("GenDegrees: " | toString sort flatten degrees I);
    print("ReducedHilbertSeries: " | toString hs);
    print("SecondsKer: " | toString(t1 - t0));
    print("SecondsHilbert: " | toString(t2 - t1));
) else (
    dep = m - pdim coker gens I;
    t2 = cpuTime();
    print("Depth: " | toString dep);
    print("SecondsDepth: " | toString(t2 - t1));
);
exit 0;
