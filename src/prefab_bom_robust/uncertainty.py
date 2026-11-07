from itertools import combinations, product
from math import comb, floor, fsum, isfinite


def _split_budget(nodes, gamma):
    if not isfinite(gamma) or not 0 <= gamma <= len(nodes):
        raise ValueError("gamma outside [0,n]")
    if len(set(nodes)) != len(nodes):
        raise ValueError("risk nodes must be unique")
    whole = floor(gamma)
    return whole, gamma - whole


def _vertex_count(nodes, gamma):
    whole, frac = _split_budget(nodes, gamma)
    n = len(nodes)
    if whole == n:
        return 2**n
    return sum(comb(n, i) for i in range(whole + 1)) + (
        comb(n, whole) * (n - whole) if frac else 0
    )


def budget_extreme_points(nodes: tuple[str, ...], gamma: float, tol: float = 1e-10) -> list[dict[str, float]]:
    """All vertices of {z in [0,1]^n: sum(z)<=gamma}."""
    p, frac = _split_budget(nodes, gamma)
    points: list[dict[str, float]] = []
    for count in range(p + 1):
        for ones in combinations(nodes, count):
            points.append({node: float(node in ones) for node in nodes})
    if frac:
        for ones in combinations(nodes, p):
            remaining = [node for node in nodes if node not in ones]
            for partial in remaining:
                point = {node: float(node in ones) for node in nodes}
                point[partial] = frac
                points.append(point)
    for point in points:
        validate_point(point, nodes, gamma, tol)
    return points


def validate_point(point: dict[str, float], nodes: tuple[str, ...], gamma: float, tol: float = 1e-9) -> None:
    if set(point) != set(nodes):
        raise ValueError("point keys do not match nodes")
    if any(not isfinite(value) or value < 0 or value > 1 for value in point.values()):
        raise ValueError("point violates box bounds")
    if fsum(point.values()) > gamma + tol:
        raise ValueError("point violates risk budget")


def joint_extreme_points(S: tuple[str, ...], V: tuple[str, ...], gamma2: float, gamma3: float,
                         max_scenarios: int = 10000) -> list[tuple[dict[str, float], dict[str, float]]]:
    count = _vertex_count(S, gamma2) * _vertex_count(V, gamma3)
    if count > max_scenarios:
        raise ExactEnumerationUnavailable(
            f"{count} scenarios exceed safety threshold {max_scenarios}; "
            "当前没有可用的精确最坏情景认证方法"
        )
    return list(product(budget_extreme_points(S, gamma2), budget_extreme_points(V, gamma3)))


class ExactEnumerationUnavailable(RuntimeError):
    pass
