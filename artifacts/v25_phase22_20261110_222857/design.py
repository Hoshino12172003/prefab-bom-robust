"""Frozen Phase 2.2 grids and exact finite-window service evaluation."""
import csv
import json
import sys
from dataclasses import dataclass
from fractions import Fraction as F
from itertools import product
from math import lcm
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P21A = ROOT/'artifacts/v25_phase21a_20261110_214856'
P21B = ROOT/'artifacts/v25_phase21b_20261110_221400'
sys.path.insert(0,str(P21A))
import audit_joint_policy as prior
from frontier import DEMAND, RATIO, RATIO_BOUNDS, SCALES, SPEC

ONE = F(1)
WINDOW = len(DEMAND)
TOTAL = sum(DEMAND)
RAW = tuple(tuple(SPEC['battery_chain'][i]['capacity'][str(t)] for t in range(1,WINDOW+1)) for i in (1,2))
SEVERITIES = (F(1,4),F(1,2),F(3,4))
DURATIONS = {'SHORT':4,'MEDIUM':7,'LONG':11}
PREMIUMS = (F(0),F(1,20),F(1,10),F(1,5))
RATIOS = (RATIO,*RATIO_BOUNDS)
LAYERS = ('L1','L2','L3')
PASS_HOLD = 'HOLD_ALGORITHM_INNOVATION_PROBLEM_REDUCIBLE'


@dataclass(frozen=True)
class Profile:
    name: str
    levels: tuple
    duration: int
    recovery: str
    kind: str

    @property
    def factors(self):
        curve = [ONE]*self.duration
        if self.recovery=='GRADUAL':
            curve.extend((F(2,3),F(1,3)))
        curve.extend([F(0)]*(WINDOW-len(curve)))
        factors = tuple(tuple(ONE-s*f for f in curve) for s in self.levels)
        assert all(0<=g<=1 for layer in factors for g in layer)
        assert all(a<=b for a,b in zip(factors[0],factors[0][1:]))
        return factors


NR = Profile('NR',(F(0),)*3,0,'ABRUPT','NO_RISK_REFERENCE')


def formal_profiles():
    yield NR
    for layer,severity,(length,d),recovery in product(LAYERS,SEVERITIES,DURATIONS.items(),('ABRUPT','GRADUAL')):
        levels = tuple(severity if l==layer else F(0) for l in LAYERS)
        tag = f'{layer}_S{int(4*severity)}_{length}_{recovery}'
        yield Profile(tag,levels,d,recovery,'CORE' if recovery=='ABRUPT' else 'RECOVERY_SENSITIVITY')


def read(path):
    with path.open(encoding='utf-8-sig',newline='') as file:
        return list(csv.DictReader(file))


def export(name,rows):
    rows = list(rows)
    with (HERE/name).open('w',encoding='utf-8-sig',newline='') as file:
        writer = csv.DictWriter(file,list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def factors_json(profile):
    return json.dumps([[str(v) for v in layer] for layer in profile.factors],separators=(',',':'))


def scenario_row(profile):
    return dict(scenario_id=profile.name,kind=profile.kind,
        layers='|'.join(l for l,s in zip(LAYERS,profile.levels) if s),severity_L1=str(profile.levels[0]),
        severity_L2=str(profile.levels[1]),severity_L3=str(profile.levels[2]),shock_start=1 if profile.duration else '',
        duration_periods=profile.duration,horizon_fraction=str(F(profile.duration,WINDOW)),
        recovery=profile.recovery,recovery_first_full_period=(
            profile.duration+(3 if profile.recovery=='GRADUAL' else 1)) if profile.duration else 1,
        evidence_class='EXPERIMENTAL_SENSITIVITY' if profile.recovery=='GRADUAL' else (
            'EXPERIMENTAL_STRESS_TEST' if profile.duration else 'DESIGN_NO_RISK_REFERENCE'),
        factor_order='L1_release;L2_production;L3_transport',factor_paths=factors_json(profile),
        source_mechanism='Phase 2.0 frozen RSP-C; source 14-period calendar and raw capacities',
        amplitude_duration_provenance='quarter increments; ceil(14*[1/4,1/2,3/4]); shock at day 1',
        budgets='K1|K3|K5',cost_sets='all formal_cost_grid rows',
        pooled_maximin_dominated_by='')


def write_grids():
    profiles = sorted(formal_profiles(),key=lambda p:(p.kind=='RECOVERY_SENSITIVITY',p!=NR))
    rows = [scenario_row(p) for p in profiles]
    assert len(rows)==len({r['factor_paths'] for r in rows})==55
    largest_ratio=max(RATIOS)
    k=SCALES[5]
    c=np.arange(int(largest_ratio*k)+1,dtype=np.int64)
    t_max=(largest_ratio.numerator*k-largest_ratio.denominator*c)//largest_ratio.numerator
    seen={}
    strongest = {l:f'{l}_S3_LONG_GRADUAL' for l in LAYERS}
    for p,row in zip(profiles,rows):
        h,f=service_terms(p,c)
        key=(np.minimum(h,f).tobytes(),np.minimum(h,f+t_max).tobytes())
        canonical=seen.setdefault(key,p.name)
        row['canonical_service_profile']=canonical
        row['unique_service_evaluation']=canonical==p.name
        if row['kind']=='NO_RISK_REFERENCE':
            row['pooled_maximin_dominated_by']='|'.join(strongest.values())
        elif row['scenario_id']!=strongest[row['layers']]:
            row['pooled_maximin_dominated_by']=strongest[row['layers']]
    export('formal_managerial_scenario_grid.csv',rows)
    export('formal_budget_grid.csv',(dict(budget_id=f'K{d}',days=d,K=k,average_daily='429/2',
        base_c_T=str(RATIO),B_baseline=str(k*RATIO),rule='B_K=K*c_T; no total quantity cap',
        evidence_class='EXACT_DERIVED_FROM_SOURCE_DEMAND') for d,k in SCALES.items()))
    export('formal_cost_grid.csv',(dict(cost_id=f'R{i}_P{j}',c_C='1',r_PC=str(r),delta_O=str(p),c_T=str(r),
        c_O=str(r*(1+p)),ratio_role='BASE' if r==RATIO else 'EXTERNAL_MODEL_RANGE_ENDPOINT',
        ratio_provenance='Phase 2.1 BatPaC official evidence',
        premium_role='ZERO_REFERENCE' if not p else 'SENSITIVITY_ONLY',
        premium_provenance='Predeclared fractions of normalized T1 pack cost; no route estimate',
        historical_granularity_threshold_used=False) for (i,r),(j,p) in product(enumerate(RATIOS),enumerate(PREMIUMS))))
    return rows


def service_terms(profile,c,replicas=1):
    """Return H and F(C) such that Q=min(D,O+H,O+T+F(C))."""
    factors = profile.factors
    demand = 0
    p = s = full_transport = 0
    h = f = TOTAL*replicas
    for i,due in enumerate(DEMAND):
        demand += due*replicas
        remaining_due = TOTAL*replicas-demand
        h = min(h,remaining_due+full_transport)
        f = np.minimum(f,remaining_due+s)
        cap_prod = int(RAW[0][i]*replicas*factors[1][i])
        cap_trans = int(RAW[1][i]*replicas*factors[2][i])
        full_transport += cap_trans
        s = np.minimum(s+cap_trans,p)
        release = factors[0][i]
        p = np.minimum(p+cap_prod,c*release.numerator//release.denominator)
    return h,f


def fixed_service(profile,x,replicas=1):
    c,t,o=x
    h,f=service_terms(profile,c,replicas)
    return min(TOTAL*replicas,o+h,o+t+int(f))


def prices(r,premium):
    values = (ONE,r,r*(ONE+premium))
    scale = lcm(*(v.denominator for v in values))
    return scale,tuple(int(scale*v) for v in values)


def exact_cover(profiles,k,r,premium,replicas=1,allow_t1=True,terms=None):
    """Independent finite first-stage certificate. No optimizer and no recourse MILP."""
    budget = r*k
    c = np.arange(int(budget)+1,dtype=np.int64)
    if terms is None:
        terms = [service_terms(s,c,replicas) for s in profiles]
    h = min(v[0] for v in terms)
    f = np.minimum.reduce([v[1][:len(c)] for v in terms])
    scale,coef = prices(r,premium)
    rhs = int(budget*scale)

    def requirement(z):
        o = max(0,z-h)
        if allow_t1:
            t = np.maximum(0,z-o-f)
        else:
            o = np.maximum(o,z-f)
            t = np.zeros_like(c)
        cost = coef[0]*c+coef[1]*t+coef[2]*o
        j = int(np.argmin(cost))
        return int(cost[j]),(int(c[j]),int(t[j]),int(o if np.isscalar(o) else o[j]))

    lo,hi = 0,min(TOTAL*replicas,int(budget))+1
    while hi-lo>1:
        mid=(lo+hi)//2
        if requirement(mid)[0]<=rhs:
            lo=mid
        else:
            hi=mid
    spend,x=requirement(lo)
    assert spend<=rhs and (lo==TOTAL*replicas or requirement(lo+1)[0]>rhs)
    return lo,x,F(spend,scale)


def t1_screen(profiles):
    rows = []
    nr = {(d,r,premium):exact_cover([NR],SCALES[d],r,premium)
          for d,r,premium in product(SCALES,RATIOS,PREMIUMS)}
    export('formal_nr_reference_audit.csv',(dict(budget_id=f'K{d}',B=str(SCALES[d]*r),r_PC=str(r),delta_O=str(premium),
         Q_NR_star=q,min_cost_witness=str(x),minimum_cost=str(cost))
         for (d,r,premium),(q,x,cost) in nr.items()))
    for profile in profiles:
        if profile==NR:
            continue
        for r in RATIOS:
            terms = [service_terms(profile,np.arange(int(r*SCALES[5])+1,dtype=np.int64))]
            for d,premium in product(SCALES,PREMIUMS):
                k=SCALES[d]
                q,x,cost=exact_cover([profile],k,r,premium,terms=terms)
                q0,x0,cost0=exact_cover([profile],k,r,premium,allow_t1=False,terms=terms)
                assert q>=q0
                qnr=nr[d,r,premium][0]
                assert qnr>=q
                rows.append(dict(scenario_id=profile.name,kind=profile.kind,layer=next(l for l,s in zip(LAYERS,profile.levels) if s),
                    budget_id=f'K{d}',B=str(k*r),r_PC=str(r),delta_O=str(premium),Q_star=q,Q_without_T1=q0,V_T=q-q0,
                    Q_NR_star=qnr,loss_vs_NR=qnr-q,
                    min_cost_witness=str(x),no_T1_witness=str(x0),minimum_cost=str(cost),no_T1_minimum_cost=str(cost0),
                    evidence='EXACT_INTEGER_COVER_RECURRENCE'))
    export('t1_position_value_audit.csv',rows)
    return rows


def benchmark_candidates():
    return [Profile('BENCH_LONG_GRADUAL_'+''.join(map(str,steps)),tuple(F(x,4) for x in steps),
        11,'GRADUAL','STRESS_COMBINATION')
        for steps in product(range(4),repeat=3) if sum(steps)==3]


def benchmark_dominance(replicas):
    """Compare exact fixed-policy service over the entire feasible budget domain."""
    profiles = benchmark_candidates()
    k = SCALES[5]*replicas
    c = np.arange(int(RATIO*k)+1,dtype=np.int64)
    t_max = (RATIO.numerator*k-RATIO.denominator*c)//RATIO.numerator
    values = []
    for s in profiles:
        h,f=service_terms(s,c,replicas)
        values.append(np.stack((np.minimum(h,f),np.minimum(h,f+t_max))))
    audit, survivors = [],[]
    for i,s in enumerate(profiles):
        v=values[i]
        dominating=[profiles[j].name for j,w in enumerate(values) if i!=j and np.all(w<=v)
            and (np.any(w<v) or profiles[j].name<s.name)]
        if not dominating:
            survivors.append(s)
        audit.append(dict(replicas=replicas,scenario_id=s.name,dominated_or_equivalent_to='|'.join(dominating),
                          retained=not dominating,factor_paths=factors_json(s),
                          proof_domain='all integer x under K5-derived budget; T=0 and T_max endpoints'))
    return survivors,audit


def benchmark_family():
    family,dominance=[],[]
    for n in (1,2,3):
        survivors,trace=benchmark_dominance(n)
        assert [p.name[-3:] for p in survivors]==['003','300']
        dominance.extend(trace)
        if n==1:
            compound=next(p for p in benchmark_candidates() if p.name.endswith('111'))
            family.extend([('SRC_NR',1,[NR],'SOURCE_INSTANCE'),
                           ('SCENARIO_N1',1,[survivors[0]],'STRESS_TEST_BENCHMARK'),
                           ('COMPOUND_N1',1,[compound],'STRESS_TEST_BENCHMARK')])
        family.append((f'POOL_R{n}_N2',n,survivors,
                       'STRESS_TEST_BENCHMARK' if n==1 else 'REPLICATED_COMPUTATIONAL_BENCHMARK'))
    return family,dominance
