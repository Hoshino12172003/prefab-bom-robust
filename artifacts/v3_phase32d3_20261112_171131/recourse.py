"""Run the unchanged full integer model with verified RHS row updates."""

import os
from dataclasses import dataclass
from time import perf_counter

import gurobipy as gp
import numpy as np
from gurobipy import GRB

from prefab_v3 import plain_ccg as plain
from prefab_v3.base import ASSEMBLY
from prefab_v3.event_search import SearchLimit
from prefab_v3.robust import protection_inventory

from prepare import HERE, ROOT, SOURCE


@dataclass
class Witness:
    q: int
    profile: tuple[int, ...]
    loads: np.ndarray
    inventory: np.ndarray
    tag: str
    vector: np.ndarray | None = None


class Recourse:
    def __init__(self, env, base, opening, coords, policy, directory):
        self.base, self.opening, self.coords, self.policy = base, opening, coords, policy
        self.env = env
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.model = gp.Model(env=env)
        SOURCE.configure(self.model, seconds=180)
        self.block = plain.add_recourse_block(self.model, base, "recourse", (opening, {}), policy)
        self.model.setObjective(plain.on_time(self.block, base), GRB.MAXIMIZE)
        self.model.update()
        self.matrix, self.nominal_rhs, self.sense = SOURCE.matrix_rows(self.model)
        self.rows = self.risk_rows()
        constrs = self.model.getConstrs()
        self.constraints = [constrs[i] for i in self.rows]
        self.n = coords.n_receipts
        self.arcs = {a.key: a for a in base.network.arcs}
        self.objective_idx = np.array([self.block.outflow[g.id, t].index for g in base.network.groups
                                     for t in base.network.periods if t <= g.representative.due])
        self.cells = sorted({k[:2] for k in coords.keys[:self.n]})
        cells_by_t = [(*key, t) for key in self.cells for t in base.network.periods]
        self.stock_idx = np.array([self.block.inventory[k].index for k in cells_by_t])
        self.stock_lb = np.array([self.block.inventory[k].LB for k in cells_by_t])
        self.stock_ub = np.array([self.block.inventory[k].UB for k in cells_by_t])
        self.cumulative = np.array([[k[:2] == j[:2] and j[2] <= k[2] for j in coords.keys[:self.n]]
                                    for k in cells_by_t], dtype=np.int64)
        self.lb, self.ub = map(np.array, (self.model.getAttr("LB"), self.model.getAttr("UB")))
        self.calls = []
        self.proof = self.verify_monotonicity()
        self.zero = self.verify_zero()

    def risk_rows(self):
        csc = self.matrix.tocsc()
        arcs = {arc.key: arc for arc in self.base.network.arcs}
        rows = []
        for i, key in enumerate(self.coords.keys):
            if i < self.coords.n_receipts:
                index = self.block.inventory[key].index
                lo, hi = csc.indptr[index:index+2]
                plus = csc.indices[lo:hi][csc.data[lo:hi] == 1]
                assert len(plus) == 1 and self.sense[plus[0]] == "="
                row = int(plus[0])
                node, item, t = key
                expected = self.opening[key]
                if t == self.base.network.periods[0]:
                    expected += self.base.network.initial.get((node, item), 0)
                    expected += protection_inventory(self.policy).get((node, item), 0)
                assert self.nominal_rhs[row] == expected
            else:
                arc = arcs[key[:2]]
                assert arc.key != ASSEMBLY
                indices = {self.block.flow[(*arc.key, p, key[2])].index for p in arc.recipes}
                first = min(indices)
                row = int(csc.indices[csc.indptr[first]])
                actual = self.matrix.getrow(row)
                assert set(actual.indices) == indices and np.all(actual.data == 1)
                assert self.sense[row] == "<" and self.nominal_rhs[row] == arc.capacity[key[2]]
            rows.append(row)
        assert len(set(rows)) == len(rows)
        return np.array(rows)

    def rhs(self, profile):
        rhs = self.nominal_rhs.copy()
        rhs[self.rows] += np.array(profile, dtype=np.int64) - self.coords.nominal
        return rhs

    def verify_against_builder(self, profiles):
        for profile in profiles:
            with gp.Model(env=self.env) as check:
                plain.add_recourse_block(check, self.base, "recourse",
                                         self.coords.profiles(profile, self.opening), self.policy)
                check.update()
                a, h, s = SOURCE.matrix_rows(check)
                assert (self.matrix != a).nnz == 0 and np.array_equal(self.rhs(profile), h)
                assert np.array_equal(s, self.sense) and np.array_equal(check.getAttr("LB"), self.lb)
                assert np.array_equal(check.getAttr("UB"), self.ub)
                assert check.getAttr("VType") == self.model.getAttr("VType")

    def verify_monotonicity(self):
        net = self.base.network
        extra = protection_inventory(self.policy)
        out = []
        for node, sku in self.cells:
            assert (node, sku) not in net.external
            assert all(g.representative.node != node or g.id != sku for g in net.groups)
            lo, hi = net.inventory_bounds[node, sku]
            possible_inflow = sum(a.capacity[t] for a in net.arcs for t in net.periods
                                  if a.destination == node and sku in a.recipes and t+a.lead in net.periods)
            fixed_total = sum(q for (n, p, _), q in self.opening.items() if (n, p) == (node, sku))
            assert all(q >= 0 for q in (fixed_total, possible_inflow))
            gross = net.initial.get((node, sku), 0) + extra.get((node, sku), 0) + fixed_total + possible_inflow
            assert gross <= hi
            out.append(dict(node=node, sku=sku, policy=self.policy, inventory_ub=hi, inventory_lb=lo,
                            nominal_fixed_receipts=fixed_total, endogenous_inflow_bound=possible_inflow,
                            gross_stock_bound=gross, inventory_upper_slack=hi-gross))
        return out

    def matrix_check(self, vector, rhs):
        lhs = self.matrix @ vector
        assert np.all(vector >= self.lb) and np.all(vector <= self.ub)
        assert np.array_equal(lhs[self.sense == "="], rhs[self.sense == "="])
        assert np.all(lhs[self.sense == "<"] <= rhs[self.sense == "<"])
        assert np.all(lhs[self.sense == ">"] >= rhs[self.sense == ">"])
        return lhs

    def verify_zero(self):
        net, block = self.base.network, self.block
        v = np.zeros(self.model.NumVars, dtype=np.int64)
        extra = protection_inventory(self.policy)
        assert self.model.NumVars == self.model.NumIntVars == 75810
        for (node, sku, t), var in block.inventory.items():
            first = net.periods[0]
            prior = net.initial.get((node, sku), 0) + extra.get((node, sku), 0) if t == first else (
                v[block.inventory[node, sku, t-1].index])
            v[var.index] = prior + self.opening.get((node, sku, t), 0)
        for t, var in block.unassigned.items():
            v[var.index] = self.arcs[ASSEMBLY].capacity[t]
        for g in net.groups:
            v[block.shortfall[g.id, g.representative.due].index] = len(g.orders)
        lhs = self.matrix_check(v, self.nominal_rhs)
        assert v[self.objective_idx].sum() == 0
        witness = Witness(0, self.coords.nominal, lhs[self.rows[self.n:]], v[self.stock_idx], "zero")
        assert self.feasible(witness, (0,)*len(self.coords.nominal))
        return witness

    def feasible(self, w, profile):
        change = self.cumulative @ (np.array(profile[:self.n]) - w.profile[:self.n])
        return (np.all(w.loads <= profile[self.n:]) and np.all(w.inventory + change >= self.stock_lb)
                and np.all(w.inventory + change <= self.stock_ub))

    def bank_bound(self, bank, profile, target):
        """Reuse full integer witnesses via their changed-row projections."""
        for w in reversed(bank):
            if w.q >= target and self.feasible(w, profile):
                return w
        return None

    def solve(self, profile, kind, seconds=180, capture_vector=False):
        if seconds <= 0:
            raise SearchLimit("wall time limit before solve")
        started = perf_counter()
        model = self.model
        tag = f"{len(self.calls)+1:05d}_{kind}"
        path = self.directory / f"{tag}.log"
        path.write_text("", encoding="utf-8")
        model.Params.LogFile = os.path.relpath(path, ROOT)
        model.Params.TimeLimit = seconds
        rhs = self.rhs(profile)
        model.setAttr("RHS", self.constraints, rhs[self.rows].tolist())
        model.optimize()
        status = model.Status
        record = dict(tag=tag, kind=kind, status=status, solver_seconds=model.Runtime,
                      log=path.relative_to(HERE).as_posix(), profile=profile)
        self.calls.append(record)
        if status != GRB.OPTIMAL or model.MIPGap != 0 or model.ObjVal != model.ObjBound:
            if status == GRB.TIME_LIMIT:
                record["wall_seconds"] = perf_counter()-started
                raise SearchLimit("Gurobi time limit")
            raise RuntimeError(f"{tag}: uncertified Gurobi status {status}")
        raw = np.array(model.getAttr("X"))
        integer = np.rint(raw).astype(np.int64)
        residual = max(model.ConstrVio, model.BoundVio, model.IntVio, float(np.max(np.abs(raw-integer))))
        assert residual <= 1e-7
        lhs = self.matrix_check(integer, rhs)
        assert np.array_equal(model.getAttr("RHS"), rhs)
        q = int(integer[self.objective_idx].sum())
        assert q == model.ObjVal
        record.update(q=q, objective_bound=model.ObjBound, gap=model.MIPGap, residual=residual, matrix_residual=0,
                      affected_capacity_loads=lhs[self.rows[self.n:]].astype(np.int64).tolist(),
                      affected_cell_inventory=integer[self.stock_idx].tolist(),
                      wall_seconds=perf_counter()-started)
        return Witness(q, profile, lhs[self.rows[self.n:]].astype(np.int64), integer[self.stock_idx], tag,
                       integer if capture_vector else None)

    def replay_matrix(self, witness, profile):
        vector = witness.vector.copy()
        vector[self.stock_idx] += self.cumulative @ (np.array(profile[:self.n]) - witness.profile[:self.n])
        self.matrix_check(vector, self.rhs(profile))
        assert vector[self.objective_idx].sum() == witness.q

    def close(self):
        self.model.dispose()
