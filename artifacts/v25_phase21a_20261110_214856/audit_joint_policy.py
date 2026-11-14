"""Phase 2.1A read-only reconstruction and exact joint policy certificates."""
import csv
import gzip
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from collections import Counter
from fractions import Fraction
from math import lcm
from pathlib import Path
from types import SimpleNamespace

import gurobipy as gp
import numpy as np
from gurobipy import GRB

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIOR = ROOT/'artifacts/v25_phase21_20261110_212532'
sys.path.insert(0, str(PRIOR))
import run_diagnostics as prior
from frontier import LABEL, RATIO, SCALES, SUPPORT, TOTAL, no_oem_service

K = SCALES[5]
POSITIONS = prior.POSITIONS
RUN_HEADER = re.compile(rf'^{LABEL} (\S+) k=(\d+) ratio=(\S+) premium=(\S+) floor=(\d+) exact=(True|False)$', re.M)
PASS = 'PASS_POLICY_SET_WIDE_BUT_INTERPRETABLE'


def records(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def export(name, rows):
    with (HERE/name).open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest(path):
    rows = records(path)
    assert all(digest(ROOT/r['path']) == r['sha256'] for r in rows)
    return len(rows)


def budget_terms(k, ratio, premium):
    prices = (Fraction(1), ratio, ratio*(1+premium))
    scale = lcm(*(p.denominator for p in prices))
    return prices, scale, tuple(int(p*scale) for p in prices), int(ratio*k*scale)


class Captured(Exception):
    """Stop the legacy model after row construction and before the optimizer."""


class ReadOnlyCapture:
    def __init__(self, direct):
        self.direct = direct
        self.real = direct.model
        self.Params = SimpleNamespace()

    def __getattr__(self, name):
        return getattr(self.real, name)

    def message(self, _):
        pass

    def optimize(self):
        model = self.real
        model.update()
        x = self.direct.x
        columns = [model.getCol(v) for v in x]
        touching = {col.getConstr(i).index: col.getConstr(i) for col in columns for i in range(col.size())}
        pure = []
        x_indices = {v.index for v in x}
        for constraint in touching.values():
            row = model.getRow(constraint)
            if all(row.getVar(j).index in x_indices for j in range(row.size())):
                pure.append((constraint.ConstrName, constraint.Sense,
                             tuple(model.getCoeff(constraint, v) for v in x), constraint.RHS))
        raise Captured(pure, tuple(v.UB == 0 for v in x), self.direct.z.LB, self.direct.z.UB)


def archived_budget_audit(network, env):
    original = {}
    for name in ('single_buffer_capability', 'equal_cost_dominance', 'threshold_direct_checks',
                 'risk_location_policy_response', 'optimal_policy_set_ranges', 'near_optimal_policy_ranges'):
        original.update((r['run'], r) for r in records(PRIOR/f'{name}.csv'))
    assert len(original) == 336
    log_by_risk = {risk: [] for risk in ('NOM', 'L1', 'L2', 'L3')}
    for log in sorted((PRIOR/'logs').glob('*.log')):
        text = log.read_text(encoding='utf-8')
        header, = RUN_HEADER.findall(text)
        name, k, ratio, premium, floor, exact = header
        assert name == log.stem and 'Optimal solution found' in text
        if int(k) not in SCALES.values():
            continue
        archived = original.get(name)
        if archived:
            assert (archived['k'], archived['ratio'], archived['premium'], archived['target']) == (k, ratio, premium, floor)
            risk = archived['risk']
        else:
            assert name.startswith('P1_') and name.endswith('_zero')
            risk = name.split('_')[1]
        log_by_risk[risk].append((log, header, archived))
    result = []
    for risk, cases in log_by_risk.items():
        direct = prior.Direct(network, risk, env)
        capture = ReadOnlyCapture(direct)
        direct.model = capture
        for log, (name, k, ratio, premium, floor, exact), archived in cases:
            k, r, d = int(k), Fraction(ratio), Fraction(premium)
            floor, exact = int(floor), exact == 'True'
            expected_bounds = (False, False, False)
            if name.startswith('P1_'):
                expected_bounds = (True, True, True)
            if name.startswith('P2_'):
                kind = name.split('_', 3)[-1]
                mode = {label: mask for mask, label in prior.SUPPORT_NAME.items()}[kind]
                expected_bounds = tuple(not bool(mode & (1<<i)) for i in range(3))
            allowed = sum(1<<i for i, fixed in enumerate(expected_bounds) if not fixed)
            endpoint = None
            if name.startswith(('P6_', 'P7_')):
                endpoint = POSITIONS.index(archived['position']), archived['endpoint'] == 'max'
            dummy = (0, [(0, 0)]*3, [(0, 0, 0)]*6)
            try:
                direct.solve(name, k, r, d, dummy, allowed=allowed, floor=floor, exact=exact, endpoint=endpoint)
            except Captured as captured:
                pure, bounds, zlb, zub = captured.args
            else:
                raise AssertionError('optimizer call was not intercepted')
            prices, scale, coeffs, rhs = budget_terms(k, r, d)
            matches = pure == [('diagnostic_budget', '<', coeffs, rhs)] and bounds == expected_bounds
            matches = matches and (zlb, zub) == (floor, floor if exact else TOTAL)
            has_quantity = any(s == '<' and a[0] > 0 and a[0] == a[1] == a[2] and b == k*a[0]
                               for _, s, a, b in pure)
            is_economic = prices != (1, 1, 1)
            if archived:
                assert Fraction(archived['budget']) == Fraction(rhs, scale)
            phase_days = next(day for day, value in SCALES.items() if value == k)
            fixed = ';'.join(v+'=0' for v, selected in zip(POSITIONS, bounds) if selected)
            result.append(dict(label=LABEL, run=name, risk=risk, K_label=f'K{phase_days}', K_value=k,
                               K_definition=f'ceil({phase_days}*3003/14)={k}',
                               K5_definition='ceil(5*3003/14)=1073' if k == K else '',
                               semantics=(f'K{phase_days}-derived budget' if is_economic else f'K{phase_days} quantity cap'),
                               budget_B=str(Fraction(rhs, scale)), c_C=str(prices[0]), c_T=str(prices[1]),
                               c_O=str(prices[2]), premium_exact=str(d),
                               actual_constraint=f'{coeffs[0]}*x_C+{coeffs[1]}*x_T+{coeffs[2]}*x_O <= {rhs}',
                               unscaled_constraint=f'x_C+({prices[1]})*x_T+({prices[2]})*x_O <= {Fraction(rhs,scale)}',
                               captured_pure_buffer_rows=json.dumps(pure), fixed_buffer_variables=fixed,
                               quantity_cap_at_K=has_quantity, quantity_cap_1073=k == K and has_quantity,
                               cost_budget_row_present=len(pure) == 1,
                               distinct_economic_cost_row=is_economic, service_floor=floor, service_fixed=exact,
                               reconstruction_matches=matches and has_quantity != is_economic,
                               archived_log=log.relative_to(ROOT).as_posix(), archived_log_sha256=digest(log),
                               archived_buffer_sum=(sum(int(archived[v]) for v in POSITIONS) if archived else 0)))
        capture.real.dispose()
    result.sort(key=lambda r: (r['K_value'],r['run']))
    export('k_budget_semantics_audit.csv', result)
    assert len(result) == 340 and sum(r['K_value'] == K for r in result) == 306
    return result


class JointSet:
    """Exact independent integer projection with rational budgets and costs."""
    def __init__(self, risk, budget, ratio):
        scale = lcm(budget.denominator, ratio.denominator)
        self.risk, self.budget, self.ratio = risk, budget, ratio
        self.scale, self.p = scale, int(scale*ratio)
        self.budget_scaled = bound = int(scale*budget)
        assert (bound//scale)*10 < 99999
        c, t = np.meshgrid(np.arange(bound//scale+1), np.arange(bound//self.p+1), indexing='ij')
        left = bound-scale*c-self.p*t
        ok = left >= 0
        self.c, self.t, self.left = c[ok], t[ok], left[ok]
        self.base = no_oem_service(risk,self.c,self.t)

    def oem_cap(self, premium, right=False):
        d, n = premium.denominator, premium.numerator
        return np.maximum(0, (self.left*d-int(right))//(self.p*(d+n)))

    def service(self, x):
        c,t,o = x
        return min(TOTAL, int(no_oem_service(self.risk,c,t))+o)

    def joint(self, premium, target=None, right=False):
        high = self.oem_cap(premium, right)
        z = np.minimum(TOTAL,self.base+high)
        if target is None:
            target = int(z.max())
        ok = z >= target
        return target, np.column_stack((self.c[ok],self.t[ok],np.maximum(0,target-self.base[ok]),high[ok]))

    def breakpoints(self):
        z, policies = self.joint(Fraction(0))
        first_exit = first_support = first_service = None
        if np.any(policies[:,3] > 0):
            c,t,_,o = policies[policies[:,3]>0].T
            d = self.p*o
            n = self.budget_scaled-self.scale*c-self.p*t-d
            j = int(np.argmin(n/d))
            assert np.all(n*d[j] >= n[j]*d)
            first_exit = Fraction(int(n[j]),int(d[j]))
            mask = (self.c>0).astype(int)+2*(self.t>0)
            limits = []
            for kind in range(4):
                ok = mask == kind
                o = np.maximum(1,z-self.base[ok])
                d = self.p*o
                n = self.left[ok]-d
                j = int(np.argmax(n/d))
                assert np.all(n*d[j] <= n[j]*d)
                if n[j] >= 0:
                    limits.append(Fraction(int(n[j]),int(d[j])))
            first_support = min(limits)
            if self.base.max() < z:
                first_service = max(limits)
        return z, first_exit, first_support, first_service


def expand(intervals):
    widths = intervals[:,3]-intervals[:,2]+1
    i = np.repeat(np.arange(len(intervals)), widths)
    offset = np.arange(widths.sum())-np.repeat(np.cumsum(widths)-widths,widths)
    return np.column_stack((intervals[i,:2], intervals[i,2]+offset))


def intervals_text(values):
    breaks = np.flatnonzero(np.diff(values)>1)+1
    return '|'.join(str(g[0]) if len(g)==1 else f'{g[0]}-{g[-1]}' for g in np.split(values,breaks))


def coupling_rows(context, tuples):
    for fixed in range(3):
        for varying in range(3):
            if fixed == varying:
                continue
            pairs = np.unique(tuples[:,[fixed,varying]],axis=0)
            cuts = np.flatnonzero(np.diff(pairs[:,0]))+1
            for group in np.split(pairs,cuts):
                values = group[:,1]
                yield dict(**context, fixed_position=POSITIONS[fixed], fixed_value=int(group[0,0]),
                           response_position=POSITIONS[varying], minimum=int(values[0]), maximum=int(values[-1]),
                           exact_integer_intervals=intervals_text(values), feasible_values=len(values),
                           holes=int(values[-1]-values[0]+1-len(values)))


def solve(direct, name, ratio, premium, warm, expected, target=None, endpoint=None, minimize_cost=False):
    model = direct.model
    _, scale, coefficients, rhs = budget_terms(K, ratio, premium)
    for variable, coefficient in zip(direct.x, coefficients):
        model.chgCoeff(direct.budget, variable, coefficient)
    direct.budget.RHS = rhs
    model.reset()
    direct.z.LB, direct.z.UB = (0, TOTAL) if target is None else (target, target)
    for variable, quantity in zip(direct.x, warm):
        variable.Start = quantity
    direct.z.Start = expected if target is None else target
    cost = gp.LinExpr(coefficients, direct.x)
    objective, sense = direct.z, GRB.MAXIMIZE
    if endpoint is not None:
        index, high = endpoint
        objective, sense = direct.x[index], GRB.MAXIMIZE if high else GRB.MINIMIZE
    if minimize_cost:
        objective, sense = cost, GRB.MINIMIZE
    model.setObjective(objective, sense)
    log = HERE/'logs'/f'{name}.log'
    model.Params.LogFile = os.path.relpath(log)
    model.message(f'{LABEL} {name} budget={Fraction(rhs,scale)} target={target}')
    model.optimize()
    assert model.Status == GRB.OPTIMAL and model.MIPGap == 0, name
    assert abs(model.ObjVal-expected) <= 1e-7 and abs(model.ObjBound-expected) <= 1e-7, (
        name, model.ObjVal, model.ObjBound, expected)
    raw = model.getAttr('X')
    rounded = [round(v) for v in raw]
    residual = max(model.ConstrVio,model.BoundVio,model.IntVio)
    assert min(rounded) >= 0 and residual <= 1e-7 and max(abs(a-b) for a,b in zip(raw,rounded)) <= 1e-7
    x, z, realized, spend = direct.replay(rounded,(scale,coefficients,rhs),7,target or 0)
    assert z == (expected if target is None else target)
    if minimize_cost:
        assert Fraction(spend)*scale == expected
    elif endpoint is not None:
        assert x[endpoint[0]] == expected
    return dict(run=name, x_C=x[0], x_T=x[1], x_O=x[2], total_buffer=sum(x), actual_ontime=realized,
                protection_cost=spend, budget_slack=str(Fraction(rhs,scale)-Fraction(spend)),
                objective=int(expected), bound=int(expected), obj_scale=scale if minimize_cost else 1,
                status='OPTIMAL', residual=residual, exact_ledger_residual=0, runtime_s=model.Runtime,
                log=log.relative_to(HERE).as_posix())


def minimum_cost(intervals, ratio, premium):
    _, _, coefficients, _ = budget_terms(K,ratio,premium)
    # OEM cost is strictly positive, so the lowest O in each interval suffices.
    candidates = intervals[:,:3]
    values = candidates @ np.asarray(coefficients)
    best = int(np.argmin(values))
    return int(values[best]), tuple(int(q) for q in candidates[best])


def certify_joint_sets(network, env, probe, previous):
    representative, minimum, frontiers, coupling, counts = [], [], [], [], []
    with gzip.GzipFile(filename=str(HERE/'joint_optimal_policy_set.csv.gz'),mode='wb',mtime=0) as raw:
        with io.TextIOWrapper(raw,encoding='utf-8',newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(('label','risk','regime','z_star','x_C','x_T','x_O_min','x_O_max'))
            for risk in ('L1','L2','L3'):
                direct = prior.Direct(network,risk,env)
                for regime,ratio,premium in (('EQUAL',Fraction(1),Fraction(0)),
                        ('COST_ZERO',RATIO,Fraction(0)),('COST_PROBE',RATIO,probe)):
                    prefix = f'{risk}_{regime}'
                    joint = JointSet(risk, ratio*K, ratio)
                    z_star, ranges = joint.joint(premium)
                    tuples = expand(ranges)
                    assert len(tuples) > 0
                    extrema = [(int(a.min()),int(a.max())) for a in tuples.T]
                    for j,v in enumerate(POSITIONS):
                        for side, tag in enumerate(('min','max')):
                            row = previous[f'P6_{prefix}_{v}_{tag}']
                            assert int(row['z_star']) == z_star and int(row['objective']) == extrema[j][side]
                            x = tuple(int(row[v]) for v in POSITIONS)
                            assert joint.service(x) == z_star
                            assert np.any(np.all(tuples == x,axis=1))
                    ctx = dict(label=LABEL,risk=risk,regime=regime,
                               budget_semantics='K5 quantity cap' if regime=='EQUAL' else 'K5-derived budget',
                               ratio=str(ratio),premium=str(premium),budget_B=str(ratio*K),z_star=z_star)
                    writer.writerows((LABEL,risk,regime,z_star,*r) for r in ranges)
                    max_result = solve(direct,f'{prefix}_max_service',ratio,premium,tuple(tuples[0]),z_star)
                    x = tuple(max_result[v] for v in POSITIONS)
                    assert joint.service(x) == max_result['actual_ontime'] == z_star
                    ranges_width = int(np.prod([hi-lo+1 for lo,hi in extrema]))
                    counts.append(dict(**ctx, optimal_policy_count=len(tuples), ct_interval_rows=len(ranges),
                                       cartesian_box_count=ranges_width, nonoptimal_or_infeasible_box_points=ranges_width-len(tuples),
                                       service_max_log=max_result['log'], service_bound=max_result['bound']))
                    coupling.extend(coupling_rows(ctx,tuples))
                    for j,pos in enumerate(POSITIONS):
                        for side,tag in enumerate(('min','max')):
                            value = extrema[j][side]
                            warm = tuple(tuples[np.flatnonzero(tuples[:,j]==value)[0]])
                            row = solve(direct,f'{prefix}_{tag}_{pos}',ratio,premium,warm,value,z_star,(j,bool(side)))
                            assert joint.service(tuple(row[v] for v in POSITIONS)) == row['actual_ontime'] == z_star
                            representative.append(dict(**ctx, role=f'{tag}_{pos}', **row))
                    for loss in (0,1,2,5):
                        target = z_star-loss
                        _, eligible = joint.joint(premium,target=target)
                        cost,warm = minimum_cost(eligible,ratio,premium)
                        row = solve(direct,f'{prefix}_loss_{loss}_min_cost',ratio,premium,warm,cost,target,minimize_cost=True)
                        attained = joint.service(tuple(row[v] for v in POSITIONS))
                        assert attained >= row['actual_ontime'] >= target
                        frontiers.append(dict(**ctx,service_loss_allowance=loss,service_target=target,
                                              independently_attainable_ontime=attained,**row))
                        if loss == 0:
                            assert attained == row['actual_ontime'] == z_star
                            minimum.append(dict(**ctx, role='minimum_cost_service_optimal',**row))
                            representative.append(dict(**ctx, role='minimum_cost_service_optimal',**row))
                direct.model.dispose()
                print(f'Joint policies certified for {risk}',flush=True)
    export('joint_optimal_representative_policies.csv',representative)
    export('joint_policy_coupling.csv',coupling)
    export('minimum_cost_service_optimal.csv',minimum)
    export('service_cost_policy_frontier.csv',frontiers)
    export('joint_policy_set_summary.csv',counts)
    return counts, representative, minimum, frontiers, coupling


def positive_support(intervals):
    bits = (intervals[:,0]>0).astype(int)+2*(intervals[:,1]>0)
    kinds = set(bits[intervals[:,2]==0]) | set(bits[intervals[:,3]>0]+4)
    return '|'.join(SUPPORT[i] for i in sorted(kinds))


def granularity_audit():
    rows = []
    for risk in ('L2','L3'):
        for factor in (Fraction(1,2),Fraction(1),Fraction(2)):
            joint = JointSet(risk,RATIO*K*factor,RATIO)
            z, exit_at, support_at, service_at = joint.breakpoints()
            if factor == 1:
                assert exit_at == support_at == Fraction(1,12744)
                assert service_at == (Fraction(1,10773) if risk == 'L3' else None)
            for kind, threshold in (('first_individual_policy_exit',exit_at),
                                    ('first_policy_composition_breakpoint',support_at),('first_service_breakpoint',service_at)):
                z_at = z_right = at_support = right_support = ''
                if threshold is not None:
                    z_at,at = joint.joint(threshold)
                    z_right,right = joint.joint(threshold,right=True)
                    at_support,right_support = positive_support(at),positive_support(right)
                    if kind == 'first_service_breakpoint':
                        assert z_at > z_right
                    elif kind == 'first_policy_composition_breakpoint':
                        assert at_support != right_support or z_at != z_right
                rows.append(dict(label=LABEL,risk=risk,budget_multiplier=str(factor),budget_B=str(joint.budget),
                                 ratio=str(RATIO),threshold_type=kind,threshold_exact=str(threshold) if threshold is not None else '',
                                 z_at_zero=z,z_at=z_at,z_immediately_right=z_right,supports_at=at_support,supports_right=right_support))
    for row in rows:
        peers = {r['threshold_exact'] for r in rows if (r['risk'],r['threshold_type']) == (row['risk'],row['threshold_type'])}
        row['stable_under_rescaling'] = len(peers) == 1
        row['classification'] = ('INTEGER_BUDGET_GRANULARITY_THRESHOLD' if len(peers)>1 else
                                 'NO_FINITE_THRESHOLD_IN_CHECKED_BUDGETS' if peers=={''} else 'STABLE_IN_CHECKED_BUDGETS')
    export('breakpoint_granularity_audit.csv',rows)
    return rows


def main():
    input_manifest = PRIOR/'sha256_manifest.csv'
    checked = verify_manifest(input_manifest)
    original = json.loads((PRIOR/'audit.json').read_text(encoding='utf-8'))
    assert digest(prior.SOURCE) == original['source_sha256']
    assert all(digest(Path(p)) == sha for p,sha in original['input_code_sha256'].items())
    network, phase20_checked = prior.load_prospective()
    probe = Fraction(original['common_premium_probe'])
    previous = {r['run']:r for r in records(PRIOR/'optimal_policy_set_ranges.csv')}
    (HERE/'logs').mkdir(exist_ok=True)
    with gp.Env() as env:
        budget_audit = archived_budget_audit(network,env)
        if not all(r['reconstruction_matches'] for r in budget_audit):
            (HERE/'audit.json').write_text(json.dumps(dict(status='HOLD_K5_CONSTRAINT_INCONSISTENCY',
                checked_rows=len(budget_audit)),indent=2)+'\n',encoding='utf-8')
            raise SystemExit('Archived budget row failed identity check')
        k5 = [r for r in budget_audit if r['K_value']==K]
        l2 = next(r for r in k5 if r['run']=='P5_L2_K5_PROBE')
        if l2['quantity_cap_1073']:
            (HERE/'audit.json').write_text(json.dumps(dict(status='HOLD_K5_CONSTRAINT_INCONSISTENCY',
                counterexample=l2),indent=2)+'\n',encoding='utf-8')
            raise SystemExit('Economic L2 witness exceeds K5 quantity cap')
        print(f'Archived rows reconstructed: {len(budget_audit)}, including {len(k5)} K5',flush=True)
        counts,representatives,minimum,frontiers,coupling = certify_joint_sets(network,env,probe,previous)
    breakpoints = granularity_audit()
    log_files = list((HERE/'logs').glob('*.log'))
    assert len(log_files)==99
    assert all(p.read_text(encoding='utf-8').count('Optimal solution found')==1 for p in log_files)
    audit = dict(status=PASS,label=LABEL,git_sha=subprocess.check_output(['git','rev-parse','HEAD'],
                 cwd=ROOT,text=True).strip(), gurobi_version=gp.gurobi.version(), phase21_hashes_verified=checked,
                 phase20_hashes_verified=phase20_checked, phase21_manifest_sha256=digest(input_manifest),
                 phase20_manifest_sha256=original['phase20_manifest_sha256'],
                 source_zip_sha256=original['source_sha256'],source_xlsb_sha256=original['source_xlsb_sha256'],
                 unchanged_model_source_sha256=original['input_code_sha256'],
                 reconstructed_archived_rows=len(budget_audit),archived_optimizer_calls=0,
                 k5_rows=len(k5),k5_row_counts=dict(Counter(r['semantics'] for r in k5)),
                 archived_scales=dict(Counter(r['K_label'] for r in budget_audit)),
                 l2_original_budget_row=l2,common_premium=str(probe),
                 joint_contexts=counts,representative_rows=len(representatives),minimum_cost_rows=len(minimum),
                 frontier_rows=len(frontiers),coupling_rows=len(coupling),breakpoint_rows=len(breakpoints),
                 breakpoints_classification='INTEGER_BUDGET_GRANULARITY_THRESHOLD',
                 direct_diagnostic_calls=len(log_files), formal_managerial_calls=0, algorithm_calls=0,
                 max_reported_constraint_residual=max(r['residual'] for r in representatives+frontiers),
                 exact_integer_ledger_residual=0, tests='PENDING',
                 command='python -B artifacts/v25_phase21a_20261110_214856/audit_joint_policy.py')
    assert verify_manifest(input_manifest)==checked
    (HERE/'audit.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
