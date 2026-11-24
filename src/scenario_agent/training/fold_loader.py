"""Load and revalidate the frozen five outer and twenty inner policy partitions."""
from dataclasses import dataclass
import json

from ..policy_cv_protocol_v1 import require, separation_audit, stats


@dataclass(frozen=True)
class Fold:
    fold_id: str
    outer_id: str
    kind: str
    training_ids: tuple
    heldout_ids: tuple
    training_group_keys: tuple
    heldout_group_keys: tuple
    training_stats: dict
    heldout_stats: dict


class PolicyFoldLoader:
    def __init__(self, dataset):
        self.dataset = dataset
        self.outer = tuple(self._fold(f["fold_id"], f["fold_id"], "outer", f["training_pool"], f["test"])
                           for f in dataset.outer["outer_folds"])
        self.inner = tuple(self._fold(f["outer_fold_id"]+"/"+f["validation"]["policy_ids"][0],
                            f["outer_fold_id"], "inner", f["training"], f["validation"])
                           for f in dataset.inner["inner_folds"])
        require(len(self.outer) == 5 and len(self.inner) == 20, "Expected 5 outer / 20 inner folds")
        all_ids = [sid for f in self.outer for sid in f.heldout_ids]
        require(len(all_ids) == len(set(all_ids)) == 576 and set(all_ids) == dataset.features.keys(), "Outer test coverage conflict")
        for outer in self.outer:
            require(set(outer.training_ids) | set(outer.heldout_ids) == dataset.features.keys(), "Incomplete outer partition")
            seen = []
            for inner in self.for_outer(outer.fold_id):
                require(set(inner.training_ids) | set(inner.heldout_ids) == set(outer.training_ids), "Inner pool differs from outer training")
                require(not (set(inner.training_ids) | set(inner.heldout_ids)) & set(outer.heldout_ids), "Outer test in inner loop")
                seen.extend(inner.heldout_ids)
            require(len(seen) == len(set(seen)) == len(outer.training_ids), "Incomplete internal LOPO")

    def _fold(self, fid, oid, kind, train, heldout):
        groups = self.dataset.groups
        for part in (train, heldout):
            require(len(part["sample_ids"]) == len(set(part["sample_ids"])), "Repeated sample inside partition")
            require(len(part["group_keys"]) == len(set(part["group_keys"])), "Repeated ranking group")
            require(len(part["sample_ids"]) == part["stats"]["query_count"], "Partition count conflict")
            expected = {r["sample_id"] for key in part["group_keys"] for r in groups[key]["rows"]}
            require(expected == set(part["sample_ids"]), "Ranking group was split")
            require({groups[k]["policy_id"] for k in part["group_keys"]} == set(part["policy_ids"]), "Policy metadata conflict")
            actual = stats([groups[k] for k in part["group_keys"]])
            require(json.loads(json.dumps(actual)) == part["stats"], "Frozen fold statistics conflict")
        separation_audit([groups[k] for k in train["group_keys"]], [groups[k] for k in heldout["group_keys"]])
        require(len(train["policy_ids"]) == (4 if kind == "outer" else 3) and len(heldout["policy_ids"]) == 1,
                "Wrong policy counts")
        return Fold(fid, oid, kind, tuple(train["sample_ids"]), tuple(heldout["sample_ids"]),
                    tuple(train["group_keys"]), tuple(heldout["group_keys"]), train["stats"], heldout["stats"])

    def for_outer(self, outer_id):
        result = tuple(f for f in self.inner if f.outer_id == outer_id)
        require(len(result) == 4, "Outer pool must have four inner validation policies")
        return result
