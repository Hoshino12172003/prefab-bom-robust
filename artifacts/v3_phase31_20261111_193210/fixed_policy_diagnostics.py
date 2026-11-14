"""Compare fixed extreme investments on the full historical diagnostic network."""
import gurobipy as gp

from run_diagnostics import (COSTS,F,NR,NOMINAL,SOURCE,Episode,candidate,frozen,load_tables,receipts,
                             solve,source_base,write)


def main():
    frozen()
    base,_ = source_base(load_tables(SOURCE))
    opening=receipts(base.network,NOMINAL)
    u=candidate()
    k=644
    budget=k*COSTS[1]
    portfolios=((0,0,0),(int(budget),0,0),(0,k,0),(0,0,int(budget/COSTS[2])))
    shock=Episode(64,3,F(1,2))
    scenarios={"NR":NR,"L1":(shock,None,None),"L2":(None,shock,None),"L3":(None,None,shock),
               "L1_L3":(Episode(66,1,F(1,2)),None,shock)}
    rows=[]
    with gp.Env() as env:
        for x in portfolios:
            for sid,episodes in scenarios.items():
                row=solve(env,base,opening,u,k,{sid:episodes},fixed=x)
                assert (row["x_C"],row["x_T"],row["x_O"])==x
                rows.append(row)
    write("historical_fixed_policy_scenario_audit.csv",rows)


if __name__=="__main__":
    main()
