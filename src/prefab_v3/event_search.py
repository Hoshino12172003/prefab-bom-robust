"""Lazy fixed-policy event search with certified lower-bound pruning."""

from dataclasses import dataclass
from time import perf_counter


@dataclass(frozen=True)
class Atom:
    id: int
    resource: int
    mask: int
    profile: tuple[int, ...]
    code: int = 0
    rank: int = 0


@dataclass(frozen=True)
class Node:
    selected: tuple[Atom, ...]
    remaining: tuple[Atom, ...]
    room: int
    once: int
    twice: int
    resources: int
    rank: int
    profile: tuple[int, ...]
    lower: int

    def envelope(self):
        return tuple(map(min, zip(self.profile, *(e.profile for e in self.remaining))))


@dataclass(frozen=True)
class Space:
    atoms: tuple[Atom, ...]
    nominal: tuple[int, ...]
    gamma: int
    threshold: int | None = None

    def root(self):
        remaining = tuple(e for e in self.atoms if self.threshold is None or e.rank <= self.threshold)
        return Node((), remaining, self.gamma, 0, 0, 0, 0, self.nominal, 0)

    def extend(self, node, i):
        event = node.remaining[i]
        once = node.once | event.mask
        twice = node.twice | (node.once & event.mask)
        resources = node.resources | (1 << event.resource)
        rank = node.rank + event.rank
        room = node.room - 1
        remaining = tuple(
            e for e in node.remaining[i+1:]
            if not ((1 << e.resource) & resources or e.mask & twice)
            and (self.threshold is None or e.rank + rank <= self.threshold)
        ) if room else ()
        return Node(node.selected + (event,), remaining, room, once, twice, resources, rank,
                    tuple(map(min, zip(node.profile, event.profile))), node.lower)


class SearchLimit(RuntimeError):
    pass


def search(space, evaluate, bound, record, *, seeds=(), keep_ties=False, node_limit=None, seconds=None):
    """Callbacks provide certified exact service and certified all-completion lower bounds."""
    started = perf_counter()
    stack = [space.root()]
    incumbent, worst, ties = None, (), set()
    visited = pruned = updates = 0
    stop = None

    def inspect(node):
        nonlocal incumbent, worst, ties, updates
        q = evaluate(node.profile, "leaf")
        ids = tuple(e.id for e in node.selected)
        code = sum(e.code for e in node.selected)
        if incumbent is None or q < incumbent:
            incumbent, worst, ties = q, ids, {code}
            updates += 1
            record("incumbent", node, q, incumbent)
        elif q == incumbent:
            ties.add(code)

    try:
        for seed in seeds:
            inspect(seed)
        while stack:
            if node_limit is not None and visited >= node_limit:
                raise SearchLimit("node limit")
            if seconds is not None and perf_counter() - started >= seconds:
                raise SearchLimit("wall time limit")
            node = stack[-1]
            lower = max(node.lower, bound(node, incumbent))
            visited += 1
            prune = incumbent is not None and (lower > incumbent if keep_ties else lower >= incumbent)
            if prune:
                pruned += 1
                record("prune", node, lower, incumbent)
                stack.pop()
                continue
            # Save the strengthened bound even if the exact solve reaches a limit.
            node = Node(node.selected, node.remaining, node.room, node.once, node.twice,
                        node.resources, node.rank, node.profile, lower)
            stack[-1] = node
            inspect(node)
            record("visit", node, lower, incumbent)
            stack.pop()
            stack.extend(space.extend(node, i) for i in reversed(range(len(node.remaining))))
    except SearchLimit as error:
        stop = str(error)
    lower = min([n.lower for n in stack] + ([] if incumbent is None else [incumbent]), default=0)
    return dict(worst=incumbent, worst_events=worst, worst_rhs=sorted(ties),
                worst_rhs_complete=not stack and keep_ties, exact=not stack, lower_bound=lower,
                visited_nodes=visited, pruned_nodes=pruned, incumbent_updates=updates, stop=stop,
                frontier=stack, wall_seconds=perf_counter()-started)
