"""Source equation lineage, scope evidence, and exact case witnesses."""
import csv
import json
from collections import Counter
from hashlib import sha256
from pathlib import Path

from run_replication import HERE,ROOT,SOURCE,load_tables,source_base,write

PAPER=Path("external_inputs/Optimisation model for multi-item multi-echelon supply chain.pdf")
REQUEST=Path("private_inputs/attachment/已粘贴的文本.txt")
BASE="src/prefab_v3/base.py"
INTERFACE="src/prefab_v3/interface.py"
TEST="tests/test_v3_phase30_base.py"
EXACT="KEEP_EXACT"
REIMPLEMENTED="KEEP_REIMPLEMENTED"
TWOSTAGE="MODIFY_FOR_TWO_STAGE"
ROBUST="ADD_ROBUST_EXTENSION"
BUFFER="ADD_BUFFER_EXTENSION"
OBJ="APPLICATION_OBJECTIVE_REFORMULATION"


def csv_rows(path):
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def lineage(name, rows):
    columns=("symbol","source_equation","source_section","source_data_field","V3_status","V3_equation","reason",
             "implementation_file","test_id")
    write(f"qu2021_{name}_lineage.csv",[dict(zip(columns,r)) for r in rows])


def write_lineage():
    tests=("test_full_source_network_vins_and_distinct_planning_caps",
           "test_bom_override_source_and_simultaneous_generic","test_source_initial_flows_and_nested_bom",
           "test_full_replication_integer_evidence_and_rescheduling","test_prospective_buffers_and_complete_recourse_interface")
    t1,t2,t3,t4,t5=tests
    c=[
        ("generic objective","(1)","3.4","f,inv",OBJ,"V3-OBJ","Base objective obtained with unit flow/inventory weights and zero extension weights",BASE,t4),
        ("capacity","(2)","3.4","capacity_at_arc",EXACT,"V3-01","Raw arc capacity sum across qualified items",BASE,t1),
        ("opening","(3)","3.4;4.6","initial_inventories",EXACT,"V3-02","t60 input; sparse default disclosed",BASE,t3),
        ("material balance","(4)","3.4;4.6","operations;BOM;arcs;initial_flows;demands",REIMPLEMENTED,"V3-03",
         "Explicit historical receipt, source external eligibility and automotive outflow; integer replay",BASE,t3),
        ("simultaneous outputs","(5)","3.2;3.4","operations.alpha_nxy",REIMPLEMENTED,"V3-04",
         "Pairwise normalized flow equality and shared-input divisor; alpha=0 disables case rows",BASE,t2),
        ("freight equipment","(6)","3.3;3.4","products.transportation_size_s",EXACT,"V3-05",
         "All 154 source rows are 0>=0; implementation emits nonzero rows on applicable instances",BASE,t1),
        ("flow domain","(7)","3.4","arcs;products",EXACT,"V3-DOM","Nonnegative integer",BASE,t4),
        ("inventory domain","(8)","3.4","nodes;products",EXACT,"V3-DOM","Nonnegative integer",BASE,t4),
        ("automotive objective","(9)","4.6;4.9","paper weights and five quantities",EXACT,"V3-OBJ",
         "Five weighted terms; caption and body eta settings both run",BASE,t4),
        ("order shortfall","(10)","4.6","demands;OEM assembly",REIMPLEMENTED,"V3-06",
         "Literal daily residual precludes shifting; sum assembly plus shortfall attributed to original due date. A is day-specific",BASE,t4),
        ("OEM outflow","(11)","4.6","demands;os",EXACT,"V3-07","Horizon total by VIN conserved; outflow subtracts OEM finished inventory",BASE,t4),
        ("delivery deviation","(12)","4.6","demands.period_t",EXACT,"V3-08","Absolute calendar deviation charged to actual OEM outflow",BASE,t4),
        ("unused capacity weight","(13)","4.6","period_t",EXACT,"V3-09","Latest period minus current period plus one",BASE,t4),
        ("OEM capacity slack","(14)","4.6","capacity_at_arc.zp7->zp8",EXACT,"V3-10","Use plus unused equals effective OEM capacity",BASE,t4),
        ("shortfall and outflow domain","(15)","4.6","demands",EXACT,"V3-DOM","Nonnegative integer",BASE,t4),
        ("unused capacity domain","(16)","4.6","capacity_at_arc",EXACT,"V3-DOM","Nonnegative integer",BASE,t4),
        ("source planned rows","(17)","4.6;Phase 1.10","max_flow_product_per_arc;max_flow_group_per_arc",REIMPLEMENTED,
         "V3-11","Public planned rows remain ceilings; paper D60 t65 equality 40 conflicts with public cap 22",BASE,t1),
        ("documented scheduled equality","(17)","4.6","prospective documented commitment",EXACT,"V3-12",
         "Exact separate schedule input, only where evidenced",INTERFACE,t5),
        ("seat JIT","(4)","4.5","seat group at zp7",EXACT,"V3-13","OEM seat period-end inventory is zero",BASE,t4),
        ("historical dispatch","(4)","4.6","initial_flows",EXACT,"V3-14","Dispatch t plus source arc lead; no additional shortage",BASE,t3),
        ("eligible external input","(4)","public case data","nodes_inflow",REIMPLEMENTED,"V3-15",
         "Eligible integer source inflow with optional evidenced supply limits",BASE,t3),
        ("buffer opening","(3)","V3 extension","three additive buffers",BUFFER,"V3-16",
         "Separate fixed regular and additional protection opening ledgers",INTERFACE,t5),
        ("shared stage one","(3)-(16)","V3 extension","scenario configuration",TWOSTAGE,"V3-17",
         "Shared integer policy; all operating variables copied by scenario",INTERFACE,t5),
        ("risk and activation budget","new","V3 extension","caller-supplied profiles and binary activation keys",ROBUST,"V3-18",
         "Severity duration recovery and optional Gamma; prospective calibration pending",INTERFACE,t5),
        ("common service guarantee","new","V3 extension","caller score",ROBUST,"V3-19",
         "Common bound on scenario score with every source constraint intact",INTERFACE,t5),
    ]
    lineage("constraint",c)
    variables=[("f_ijpt","(7),(9)","3.4;4.6","arcs;products","V3-01 to V3-15"),
               ("inv_npt","(8),(9)","3.4;4.6","initial_inventories","V3-02/03"),
               ("os_pt","(10),(15)","4.6","demands","V3-06"),
               ("of_pt","(11),(15)","4.6","demands","V3-07"),
               ("uc_t","(14),(16)","4.6","capacity_at_arc","V3-10")]
    lineage("variable",[(*r[:4],TWOSTAGE,r[4],"Base integer domain; scenario index in the prospective interface",BASE,t4)
        for r in variables]+[
        ("dr_p","Figure 10","4.9","original and actual VIN dates",REIMPLEMENTED,"V3-08",
         "Derived assembly and outflow deviations kept separately",BASE,t4),
        ("external supply","(4)","public case","nodes_inflow",REIMPLEMENTED,"V3-15","Explicit eligible inflow",BASE,t3),
        ("x_C;x_T;x_O","new","V3 extension","investment policy",BUFFER,"V3-16","Shared integer stock additions",INTERFACE,t5),
        ("guaranteed service","new","V3 extension","caller score",ROBUST,"V3-19","Optional epigraph-side service bound",INTERFACE,t5)])
    parameters=[
        ("T","(1)-(16)","3.4;4.6","capacity_at_arc.period_t;demands.period_t","61–74"),
        ("P","(1)-(16)","3.4;4.6","products.product_p","All 28,049 raw items retained"),
        ("G;g_p","(4)-(6)","3.4","products.group_g","Seven source groups"),
        ("N","(3),(4)","3.4","nodes","All source nodes"),
        ("A","(2),(4)","3.4","arcs","All source arcs"),
        ("B","(4)","3.4","BOM.mother;BOM.child","Distinct-item nested BOM; 49 self rows recorded"),
        ("O","(4),(5)","3.4","operations","All 15 rows"),
        ("F","(2),(4)","3.4","arcs.group_g;products.group_g","Qualified material flow tuples"),
        ("l_ij","(4)","3.4","arcs.process_lead_time_l_ij","Raw lead time"),
        ("d_npt;promised date","(10)-(12)","4.6","demands","Raw VIN demand and due date"),
        ("inv_np,ini","(3)","4.6","initial_inventories.initial_inventory_I_np0","Source opening and missing-key policy"),
        ("c_ijt","(2),(14)","3.4;4.6","capacity_at_arc.capacity_c_ijt","Raw XLSB"),
        ("s_p","(6)","3.4","products.transportation_size_s","All zero in source case"),
        ("in_nxy","(4)","3.4","operations.input_quantity_in_nxy","Generic beta=0"),
        ("out_nxy","(4),(5)","3.4","operations.output_quantity_out_nxy","Operation denominator"),
        ("q_mc","(4)","3.4","BOM.individual_input_quantity_q_mc","Individual beta=1; no double charge"),
        ("alpha_ny","(4),(5)","3.4","operations.alpha_nxy","Zero disables; positive normalized equality"),
        ("beta_nxy","(4)","3.4","operations.beta_nxy","Generic versus individual choice"),
        ("history f","(4)","4.6","initial_flows","Raw quantities and dated receipts"),
        ("safety stock;max stock","(4)","Phase 1.10","initial_inventories.safety_stock;max_inventory","Apply on available keys"),
        ("planned flows","(17)","4.6;Phase 1.10","max_flow_product_per_arc;max_flow_group_per_arc","Source ceilings distinct from physical and equality"),
        ("scheduled equality","(17)","4.6","documented separate schedule","No public equality instantiated"),
        ("gamma;delta;epsilon;zeta;eta","(9)","4.6;4.9","paper Eq. 9 and scenario text/figure","Retain five weights and audit discrepant eta"),
        ("zeta_t","(12)","4.6","demands.period_t","Absolute date distance"),
        ("eta_t","(13)","4.6","period_t","T-t+1"),
        ("eligible inflow","(4)","public case","nodes_inflow","Source eligibility"),
    ]
    lineage("parameter",[(*r[:4],REIMPLEMENTED if r[0] in ("B","planned flows","eligible inflow","inv_np,ini") else EXACT,
                          f"V3 source mapping {r[0]}",r[4],BASE,t1 if r[0] not in ("B","alpha_ny","beta_nxy") else t2)
                         for r in parameters]+[
        ("risk profile;Gamma","new","V3 extension","caller-supplied scenario/budget",ROBUST,"V3-18",
         "Interface only with no frozen calibration",INTERFACE,t5),
        ("buffer costs;budget","new","V3 extension","caller-supplied",BUFFER,"V3-16","No final economic values",INTERFACE,t5)])


def evidence():
    tables=load_tables(SOURCE)
    base,_=source_base(tables)
    raw_base,_=source_base(tables,compress_vins=False)
    run=json.loads((HERE/"replication_run.json").read_text(encoding="utf-8"))
    results=run["results"]
    assert all(r["status"]=="OPTIMAL" and r["objective"]==r["bound"] and r["gap"]==0
               and r["max_exact_balance_residual"]==r["max_solver_residual"]==0 for r in results)
    a,b=results[0],results[2]
    assert a["bev_shortfall"]==1552 and b["assembly_early"]>0 and b["penalty_unassigned"]==310400
    write("deterministic_replication_results.csv",results)
    write("replication_target_comparison.csv",[
        dict(target_class="DIRECT_PAPER_TARGET",metric="A BEV unfulfilled",paper_value="1552",observed=a["bev_shortfall"],
             disposition="MATCH in total; compare timing and coefficients separately"),
        dict(target_class="DIRECT_PAPER_TARGET",metric="B late-period concentration of unused assembly",paper_value="t74",
             observed="1552 at t74",disposition="MATCH on concentration"),
        dict(target_class="XLSB_REPLICATION_TARGET",metric="B actual customer outflow off due date",paper_value="",
             observed=b["early"]+b["late"],disposition="Integer outflow reconstructed; distinguish from early assembly and unfilled VINs"),
        dict(target_class="NOT_COMPARABLE_DUE_TO_SOURCE_VERSION",metric="Table 7 upstream raw capacity t67",paper_value="490",
             observed="2058",disposition="Use Phase 1.10 raw XLSB semantics"),
        dict(target_class="NOT_COMPARABLE_DUE_TO_SOURCE_VERSION",metric="Eq.17 D60 t65 commitment",paper_value="equal 40",
             observed="upper 22",disposition="Published XLSB ceiling conflicts with display equality"),
        dict(target_class="NOT_COMPARABLE_DUE_TO_SOURCE_VERSION",metric="Scenario B affected orders deferred to t74",
             paper_value="qualitative display",observed="unfilled VINs remain shortfall; OEM slot slack at t74",
             disposition="No public VIN-level solution; display mixes deferred demand and production utilization"),
    ])
    scope=[dict(sheet=s,source_rows=len(rows),V3_rows=len(rows),status="SOURCE_ROWS_READ_AND_MAPPED")
           for s,rows in tables.items()]
    write("full_network_scope_audit.csv",scope)
    group_by_item={p:g for p,g,_ in tables["products"]}
    bom=Counter(("identity_reference" if m==c else "distinct_child",group_by_item[m],group_by_item[c])
                for m,c,_ in tables["BOM"])
    write("full_bom_restoration_audit.csv",[dict(row_class=k,mother_group=m,child_group=c,rows=n,
        treatment="excluded from manufacture; transport identity via operations" if k=="identity_reference"
        else "individual input linked at operation and carried through nested balances")
        for (k,m,c),n in sorted(bom.items())])
    n=raw_base.network
    periods=len(n.periods)
    vintotal=len(n.groups)
    delta=(vintotal-len(base.network.groups))*periods
    b22=csv_rows(ROOT/"artifacts/v25_phase22_20261110_222857/direct_de_scaling_benchmark.csv")[0]
    def size(label,values):
        return dict(model=label,source_products=len(tables["products"]),VINs=values[0],nodes=12,arcs=11,
                    BOM_rows=len(tables["BOM"]),operation_rows=len(tables["operations"]),periods=14,
                    flow_variables=values[1],inventory_variables=values[2],automotive_extension_variables=values[3],
                    total_integer_variables=values[4],total_constraints=values[5],basis=values[6])
    auto=a["shortfall_variables"]+a["outflow_variables"]+a["unassigned_variables"]
    write("full_model_size_audit.csv",[
        size("V3 solved full source compressed",(vintotal,a["flow_variables"],a["inventory_variables"],auto,a["integers"],a["constraints"],"actual Gurobi counts")),
        size("V3 explicit VIN index",(vintotal,a["flow_variables"]+delta,a["inventory_variables"]+delta,auto+2*delta,
             a["integers"]+4*delta,a["constraints"]+delta+2*(vintotal-len(base.network.groups)),"counted from exact active index sets; full explicit solve not executed")),
        size("QU2021 published complete case",(28000,"","","","","","paper network/input scale; exact solver dimensions not reported")),
        size("Phase 2 focal NR",(3003,"","","",b22["integer_variables"],b22["constraints"],"Phase 2.2 Gurobi archive")),
    ])
    plan=[r for r in csv_rows(HERE/"A_NO_RESCHEDULE_VIN_schedule.csv") if r["delivery"]]
    by_vin={str(o.vin):dict(o.bom) for g in n.groups for o in g.orders}
    seat=lambda r:next(p for p in by_vin[r["vin"]] if group_by_item[p]=="seat")
    first=plan[0]
    same=next(r for r in plan if r["promised"]!=first["promised"] and by_vin[r["vin"]]==by_vin[first["vin"]])
    unlike=next(r for r in plan if r["promised"]!=first["promised"] and seat(r)!=seat(first))
    witness=[
        dict(test="same BOM date swap",vin_a=first["vin"],vin_b=same["vin"],date_a=first["promised"],date_b=same["promised"],
             effect=f"feasible with same component/Pack and capacity path; delivery penalty +{200*abs(int(first['promised'])-int(same['promised']))}"),
        dict(test="different seat date swap",vin_a=first["vin"],vin_b=unlike["vin"],date_a=first["promised"],date_b=unlike["promised"],
             effect=f"same seat receipts leave -1 {seat(unlike)} at first assembly date; exact seat-JIT violation"),
    ]
    write("full_model_reducibility_witnesses.csv",witness)
    write_lineage()


if __name__=="__main__":
    evidence()
