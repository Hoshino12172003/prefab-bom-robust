"""Materialize the frozen Phase 3.1 constructive witness at every worst RHS."""
import gzip
import json
from collections import Counter
from fractions import Fraction as F
from time import perf_counter

import gurobipy as gp
import numpy as np

import catalog_d1 as cat
from run_d1 import FROZEN, HERE, ROOT, PLAIN, load, rhs
from prefab_v25.data import CELL, COMPONENT_ARC, OEM, PACK, PROD, T1
from prefab_v3.base import ASSEMBLY


def max_schedule(base, profile, x, caps, due):
    receipts, factors = profile
    prod, ship = cat.ARC
    cells = [base.network.initial[PROD,p]+a*x[0] for p,a in zip(CELL,(10,6,4))]
    at_t1 = base.network.initial[T1,PACK]+x[1]
    at_oem = base.network.initial[OEM,PACK]+x[2]
    delayed_prod = delayed_ship = 0
    schedule = []
    for t in cat.U.periods:
        for i,p in enumerate(CELL):
            cells[i] += receipts.get((PROD,p,t),0)
        at_t1 += receipts.get((T1,PACK,t),0)+delayed_prod
        at_oem += receipts.get((OEM,PACK,t),0)+delayed_ship
        delivered = min(due[t],at_oem)
        at_oem -= delivered
        delayed_ship = min(at_t1,int(caps[ship][t]*factors.get((*ship,t),1)))
        at_t1 -= delayed_ship
        delayed_prod = min(int(caps[prod][t]*factors.get((*prod,t),1)),
                           *(q//a for q,a in zip(cells,(10,6,4))))
        cells = [q-a*delayed_prod for q,a in zip(cells,(10,6,4))]
        schedule.append((delayed_prod,delayed_ship,delivered))
    return tuple(schedule)


def replay_policy(env, base, opening, metadata, by_id, policy, source):
    start = perf_counter()
    ref = cat.read(HERE/f"{policy}_reference.json")
    x = tuple(ref["policy"])
    keys,nominal = tuple(map(tuple,metadata["schema"])),tuple(map(F,metadata["nominal_signature"]))
    n = base.network
    periods = cat.U.periods
    caps = {a.key:a.capacity for a in n.arcs}
    seats = {p for p,g in base.products.items() if g=="seat"}
    seat_arc = ("seat-supplier_inv",OEM)
    excluded = {ASSEMBLY,COMPONENT_ARC,*cat.ARC,seat_arc}
    dispatch = {tuple(k):v for k,v in source["dispatch"]}
    external = {tuple(k):v for k,v in source["supply"]}
    due = Counter()
    with gp.Model("constructive_reference_replay",env=env) as model:
        b = PLAIN.add_recourse_block(model,base,"replay",(opening,{}),x)
        model.update()
        A,original,senses = FROZEN.matrix_rows(model)
        lower,upper = (np.asarray(model.getAttr(a)) for a in ("LB","UB"))
        v0 = np.zeros(model.NumVars,dtype=np.int64)
        for k,v in b.flow.items():
            if k[:2] not in excluded:
                v0[v.index] = dispatch.get(k,0)
        for k,v in b.external.items():
            v0[v.index] = external.get(k,0)
        bev = {}
        assemblies = Counter()
        def release(v,g,t,q):
            order = g.representative
            v[b.flow[*ASSEMBLY,g.id,t].index] = q
            v[b.outflow[g.id,t].index] = q
            v[b.shortfall[g.id,t].index] = len(g.orders)-q
            seat, = [(p,k) for p,k in order.bom if p in seats]
            v[b.flow[*seat_arc,seat[0],t].index] += q*seat[1]
        for g in n.groups:
            t = g.representative.due
            if (PACK,1) in g.representative.bom:
                bev.setdefault(t,[]).append(g)
                due[t] += len(g.orders)
            else:
                release(v0,g,t,len(g.orders))
                assemblies[t] += len(g.orders)
        # The final rows are the inventory recurrences. Confirm their exact columns.
        inv = tuple(b.inventory.items())
        offset = model.NumConstrs-len(inv)
        inventory_index = np.array([v.index for _,v in inv])
        inv_row = {k:offset+i for i,(k,_) in enumerate(inv)}
        assert [k[-1] for k,_ in inv]==list(periods)*(len(inv)//len(periods))
        inv_matrix = A[offset:,inventory_index].tocoo()
        expected = {(i,i,1) for i in range(len(inv))} | {
            (i,i-1,-1) for i in range(len(inv)) if i%len(periods)}
        assert set(zip(inv_matrix.row,inv_matrix.col,inv_matrix.data))==expected
        capacity_row = {}
        for a in cat.ARC:
            for t in periods:
                v = b.flow[*a,PACK,t].index
                found = [i for i in A[:,v].nonzero()[0] if senses[i]=="<" and
                         A[i].nnz==1 and A[i,v]==1 and original[i]==caps[a][t]]
                assert len(found)==1
                capacity_row[*a,t] = found[0]
        deadlines = {g.id:g.representative.due for g in n.groups}
        score = np.array([v.index for (g,t),v in b.outflow.items() if t<=deadlines[g]])
        cache = {}
        result = []
        for id_ in ref["ties"]:
            profile = rhs(by_id[id_],keys,nominal,opening)
            receipts,factors = profile
            schedule = max_schedule(base,profile,x,caps,due)
            receipt_delta = tuple((inv_row[k],q-opening.get(k,0)) for k,q in receipts.items() if q!=opening.get(k,0))
            assert all(v==int(v) for pair in receipt_delta for v in pair)
            key = schedule,receipt_delta
            if key not in cache:
                vector = v0.copy()
                for t,(p,s,d) in zip(periods,schedule):
                    vector[b.flow[*cat.ARC[0],PACK,t].index] = p
                    vector[b.flow[*cat.ARC[1],PACK,t].index] = s
                    vector[b.unassigned[t].index] = caps[ASSEMBLY][t]-assemblies[t]-d
                    remaining = d
                    for g in bev.get(t,[]):
                        take = min(remaining,len(g.orders))
                        release(vector,g,t,take)
                        remaining -= take
                    assert remaining==0
                actual = original.copy()
                for row,change in receipt_delta:
                    actual[row] += change
                rhs_inventory = actual[offset:]-(A@vector)[offset:]
                inv_values = np.cumsum(rhs_inventory.reshape(-1,len(periods)),axis=1).ravel()
                assert np.all(inv_values==np.rint(inv_values))
                vector[inventory_index] = inv_values.astype(np.int64)
                assert np.all(lower<=vector) and np.all(vector<=upper)
                lhs = A@vector
                unchanged_le = senses=="<"
                unchanged_le[list(capacity_row.values())] = False
                assert np.all(lhs[senses=="="]==actual[senses=="="])
                assert np.all(lhs[senses==">"]>=actual[senses==">"])
                assert np.all(lhs[unchanged_le]<=actual[unchanged_le])
                q = int(vector[score].sum())
                assert q==ref["worst"]
                cache[key] = (len(cache)+1,q,lhs[list(capacity_row.values())])
            witness,q,load_values = cache[key]
            for (origin,dest,t),usage in zip(capacity_row,load_values,strict=True):
                assert usage<=float(caps[origin,dest][t]*factors.get((origin,dest,t),1))
            result.append(dict(label=cat.LABEL,policy=policy,rhs_class_id=id_,Q=q,
                               reference_witness_group=witness,integer_matrix_residual=0,solver_calls=0))
    print(policy,"constructive witnesses",len(result),"unique flow/receipt certificates",len(cache),flush=True)
    return result,dict(rows=len(result),distinct_witnesses=len(cache),seconds=perf_counter()-start,residual=0)


def main():
    metadata,rows,base,opening = load()
    by_id = {r["rhs_class_id"]:r for r in rows}
    path = ROOT/"artifacts/v25_phase20_20261110_203851/FULL28000_witness.json.gz"
    with gzip.open(path,"rt",encoding="utf-8") as f:
        source = json.load(f)
    combined, timing = [],{}
    with FROZEN.env() as env:
        for p in cat.POLICIES:
            records, timing[p] = replay_policy(env,base,opening,metadata,by_id,p,source)
            combined.extend(records)
    cat.write("reference_tie_matrix_replay.csv",combined)
    cat.dump("reference_tie_matrix_replay.json",timing)


if __name__=="__main__":
    main()
