from itertools import combinations, product
from math import floor


def budget_extreme_points(nodes: tuple[str, ...], gamma: float, tol: float = 1e-10) -> list[dict[str, float]]:
    """All vertices of {z in [0,1]^n: sum(z)<=gamma}."""
    n = len(nodes)
    if gamma < -tol or gamma > n + tol:
        raise ValueError("gamma outside [0,n]")
    gamma = min(float(n), max(0.0, gamma))
    p = floor(gamma + tol)
    frac = gamma - floor(gamma)
    points: list[dict[str, float]] = []
    for count in range(0, min(p, n) + 1):
        for ones in combinations(nodes, count):
            points.append({node: float(node in ones) for node in nodes})
    if frac > tol and p < n:
        for ones in combinations(nodes, p):
            remaining = [node for node in nodes if node not in ones]
            for partial in remaining:
                point = {node: float(node in ones) for node in nodes}
                point[partial] = frac
                points.append(point)
    unique = {tuple(round(p[node], 12) for node in nodes): p for p in points}
    result = list(unique.values())
    for point in result:
        validate_point(point, nodes, gamma, tol)
    return result


def validate_point(point: dict[str, float], nodes: tuple[str, ...], gamma: float, tol: float = 1e-9) -> None:
    if set(point) != set(nodes):
        raise ValueError("point keys do not match nodes")
    if any(value < -tol or value > 1 + tol for value in point.values()):
        raise ValueError("point violates box bounds")
    if sum(point.values()) > gamma + tol:
        raise ValueError("point violates risk budget")


def joint_extreme_points(S: tuple[str, ...], V: tuple[str, ...], gamma2: float, gamma3: float,
                         max_scenarios: int = 10000) -> list[tuple[dict[str, float], dict[str, float]]]:
    eta = budget_extreme_points(S, gamma2)
    xi = budget_extreme_points(V, gamma3)
    count = len(eta) * len(xi)
    if count > max_scenarios:
        raise ExactEnumerationUnavailable(
            f"{count} scenarios exceed safety threshold {max_scenarios}; "
            "当前没有可用的精确最坏情景认证方法"
        )
    return list(product(eta, xi))


class ExactEnumerationUnavailable(RuntimeError):
    pass
