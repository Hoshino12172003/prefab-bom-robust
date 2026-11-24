"""Public baseline names; keep the existing audited implementations shared."""
from .baseline_models import CatalogHistoryBaseline, RuleBasedBaseline


def make_pairwise_ranker(*args, **kwargs):
    raise NotImplementedError("PAIRWISE_RANKING_DEFERRED")


__all__ = ["CatalogHistoryBaseline", "RuleBasedBaseline", "make_pairwise_ranker"]
