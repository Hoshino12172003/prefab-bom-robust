"""Follow-up overlap tests using the same frozen severities, dates, and resources."""
from concurrent.futures import ProcessPoolExecutor

from design import overlap_scenarios
from run_matrix import init,solve_scenario,verify_frozen


if __name__=="__main__":
    verify_frozen()
    with ProcessPoolExecutor(max_workers=3,initializer=init) as pool:
        for name in pool.map(solve_scenario,overlap_scenarios()):
            print(f"{name}: 20 fixed policies certified",flush=True)
