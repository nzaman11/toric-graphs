"""Parsers for Macaulay2 text output (ideals, Hilbert series, 'Key: value' dumps)."""

import re
from collections import Counter
from pathlib import Path


def read_blocks(path: str | Path) -> list[dict[str, str]]:
    """Read a file of 'Key: value' lines grouped into records.

    A new record starts at every 'GraphNumber:' line, so both the '====' separated
    dumps and the edge-grouped task5 files parse the same way.
    """
    recs: list[dict[str, str]] = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^(\w+): (.*)$", line)
        if not m:
            continue
        key, val = m.groups()
        if key == "GraphNumber":
            recs.append({})
        if recs:
            recs[-1][key] = val.strip()
    return recs


def h_vector(hilbert_series: str) -> list[int]:
    """Numerator coefficients of a reduced Hilbert series '(1+3*T-T^2)/((1-T)^8)'."""
    m = re.match(r"^\((.*)\)/\(\(1-T\)\^\d+\)$", hilbert_series.replace(" ", ""))
    if not m:
        raise ValueError(f"unrecognized Hilbert series: {hilbert_series}")
    coeffs: Counter[int] = Counter()
    for term in m.group(1).replace("-", "+-").split("+"):
        if not term:
            continue
        t = re.match(r"^(-?)(\d*)\*?(T(?:\^(\d+))?)?$", term)
        if not t:
            raise ValueError(f"unrecognized term {term!r} in {hilbert_series}")
        sign, num, tpart, exp = t.groups()
        coef = int(num) if num else 1
        deg = 0 if not tpart else int(exp or 1)
        coeffs[deg] += -coef if sign else coef
    return [coeffs[d] for d in range(max(coeffs) + 1)]


def hilbert_dim(hilbert_series: str) -> int:
    return int(re.search(r"\(1-T\)\^(\d+)", hilbert_series).group(1))


def ideal_generators(ideal: str) -> list[str]:
    """'ideal(a-b,c-d)' -> ['a-b', 'c-d']; 'ideal()' or 'ideal 0' -> []."""
    s = ideal.strip()
    if not s.startswith("ideal(") or not s.endswith(")"):
        return []
    body = s[len("ideal("):-1].strip()
    return [g.strip() for g in body.split(",")] if body else []


def binomial_degree(binomial: str) -> int:
    """Total degree of the first monomial of a homogeneous binomial like 'e_1*e_3^2-e_2*e_4*e_5'."""
    first = re.split(r"(?<!^)-", binomial.lstrip("-"), maxsplit=1)[0]
    deg = 0
    for factor in first.split("*"):
        if re.match(r"^\d+$", factor):
            continue
        base_exp = factor.split("^")
        deg += int(base_exp[1]) if len(base_exp) == 2 else 1
    return deg
