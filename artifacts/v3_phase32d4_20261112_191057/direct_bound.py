"""Independent algebraic and Gurobi bounds on the full Direct DE."""

import gurobipy as gp

from prefab_v3.e4_ccg import Prefix
from direct_de import OUT, Template, add_direct, check_solution
from run import HERE, SOURCE, Coordinates, frozen_catalog, optimize_model, read, spend


def main():
    SOURCE.init()
    coords=Coordinates()
    identity=read(OUT / "model_identity.json")
    mps=OUT / identity["path"]
    assert frozen_catalog.digest(mps)==identity["sha256"]
    code=16106127360
    assert code in identity["ordered_rhs"]
    profile=coords.profiles(coords.code_profile(code),SOURCE.OPENING)
    analytic_ub=Prefix(SOURCE.BASE).upper(profile,(0,0,0))[1]
    with SOURCE.env() as env,gp.Model(env=env) as model:
        add_direct(model,coords,[code])
        ub,vector,metrics=optimize_model(model,OUT / "independent_one_block.log")
        spend(tuple(map(int,vector[:3])))
        template=Template(env,coords)
    start=read(OUT / "feasible_start.json")
    assert frozen_catalog.digest(OUT / "full_start.mst.gz")==start["sha256"]
    assert start["full_blocks_matrix_verified"]==355 and start["matrix_residual"]==0
    lb=start["objective"]
    assert lb==ub==analytic_ub
    incumbent=OUT / "conservative_retry/full.sol.gz"
    replay=check_solution(incumbent,template,identity["ordered_rhs"]) if incumbent.exists() else None
    if replay:
        assert replay["objective"]==lb
        replay["sha256"]=frozen_catalog.digest(incumbent)
    frozen_catalog.dump(OUT / "bound_certificate.json",dict(exact=True,lower=lb,upper=ub,
        source_upper="INDEPENDENT_DIRECT_WORST_BLOCK_AND_FROZEN_SEAT_PREFIX",
        worst_block_rhs=code,upper_model=metrics,source_lower="ALL_355_BLOCK_MATRIX_REPLAY",
        mps_sha256=identity["sha256"],start_sha256=start["sha256"],cli_incumbent_replay=replay))
    print("Full Direct DE independently bounded at",lb,flush=True)


if __name__=="__main__":
    main()
