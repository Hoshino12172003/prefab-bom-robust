"""Importable V1 view contracts and serializable projection preprocessor."""
from ..policy_cv_protocol_v1 import require
from .dataset import FEATURE_NAMES, FEATURE_SPECS
from .preprocessing import FoldPreprocessor


def feature_views():
    risk=tuple(s.name for s in FEATURE_SPECS if s.source in
               ("raw_events","verified signature","raw_events + original capacity/receipts"))
    master=("buffer_C","buffer_T","buffer_O","master_budget","master_remaining_budget")
    views={"Risk-only":risk,"Risk+Master":tuple(n for n in FEATURE_NAMES if n in risk+master),"Full-78":FEATURE_NAMES}
    require(tuple(map(len,views.values()))==(39,44,78),"View specification drift")
    return views


class ViewPreprocessor(FoldPreprocessor):
    def __init__(self,view):
        super().__init__()
        self.view=view
        self.names=feature_views()[view]
        self.indices=[FEATURE_NAMES.index(n) for n in self.names]

    def fit(self,batch,*,fold):
        super().fit(batch,fold=fold)
        self.state["feature_view"]=self.view
        self.state["model_feature_order"]=list(self.names)+[n+"__missing" for n in self.names]
        return self

    def transform(self,batch,mode):
        full=super().transform(batch,mode)
        return full[:,self.indices+[78+i for i in self.indices]]
