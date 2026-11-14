# V3 Phase 3.2A 基础精确情景块 C&CG

**状态：PASS_PLAIN_CCG_EXACT_BASELINE**  
证据范围为 **FINITE_SCENARIO_EXACT_CCG_BASELINE** 和 **STRESS_TEST_ONLY**。

## 冻结实例与初始化

沿用 Phase 3.1R 的历史 t=60 状态、t=61–74 完整整数追索和原 4、8、16 情景嵌套集合。全网包含 28,000 VIN、28,049 物料、12 节点及 11 条弧。BOM、供应及装配容量、到期日、提前期、初始库存、历史在途、计划上限和重排全部通过冻结的模型构造函数进入每个情景块。第一阶段保留整数 \((x_C,x_T,x_O)\)、10/6/4 组件套件和约束 \(x_C+(27/19)x_T+(297/190)x_O\le17388/19\)。目标是最大化最坏情景准时出库量。

原有限集合全为双分支压力情景。单块初始化选择三个集合共有的 DE_ENGINE_68，作为较晚冲击的参考轨迹。双块初始化在同一参考轨迹上再加入较早的 DE_GEAR_61，其第 61 日同时降低变速箱运输与座椅配送能力。两条初始化轨迹由分支和日期直接指定；其选择在所有新求解之前固化，且都属于原集合。首轮分离和每轮后续分离以冻结目录顺序逐情景重新求解全网整数追索。精确最坏值并列时按情景 ID 字典序取第一项。所有并列项均保留在日志中。

## 界与有限终止

对主问题选中集合 \(\Omega_k\)，使用共享投资变量 \(x\) 和整数准时交付保证量 \(\eta\)，每个情景有独立的生产、运输、库存、订单、重排和装配追索变量。连接约束是 \(\eta\le\sum_{g,t\le d_g}\mathrm{outflow}_{g,t,\omega}\)。主问题得到整数全局最优值后，记录为 \(UB_k\)。

任一完整模型可行解投影到当前场景块仍可行，故 \(Z^*\le UB_k\)。固定当前最优政策，在整个 \(\Omega\) 上分别优化整数追索，最小的精确值 \(W(x^k)\) 是该政策可行的服务保证。历史最大值 \(LB_k=\max_{i\le k}W(x^i)\) 满足 \(LB_k\le Z^*\)。同值时保留首次达到该下界的政策。场景块累加导致 \(UB_k\) 非增，保留最佳已验证政策使 \(LB_k\) 非减。

若 \(UB_k-LB_k>10^{-6}\)，则 \(W(x^k)\le LB_k<UB_k\)。已进入主问题的场景对 \(x^k\) 均可支撑 \(UB_k\)，因此严格违反的最坏情景必在当前主问题之外。每轮只加入一个场景，至多加入到完整集合。达到容差后，重新从空的求解器模型构建并求解最终政策的全部整数追索，复核其最小值恰好等于 \(LB_k\)。每次求解要求 Gurobi OPTIMAL、目标等于认证界、相对和绝对间隙为零，并以取整后的解向量核对变量界、完整稀疏矩阵和实际准时出库目标。

## 独立验证与资源口径

Direct DE 独立构建所有情景块的投资联结和服务表达式，并另行逐情景验证其代表政策。两条路径共用冻结的物理模型。核对了每个 DE 与旧归档的情景顺序、约束数、整数变量数、非零系数数、Gurobi 模型指纹和最优值。每个主问题和每个独立追索都核对其完整块的维数和整数域。用本轮 Direct DE 全局最优值对所有迭代逐行核对 \(LB_k\le Z^{DE}\le UB_k\)。

统一使用 Gurobi 13.0.1、1 线程、种子 20261110、默认 presolve、可行性/整数/最优性容差 10⁻⁹、MIPGap 和 MIPGapAbs 均为 0、单次求解 TimeLimit 90 秒、SoftMemLimit 3 GB。每个方法与情景数的组合均在同一台机器的独立进程中串行执行。端到端时间包括建模、求解、矩阵核验及全情景终止复核。输入工作簿读取和 SHA-256 预检在计时前完成。进程峰值内存使用 Windows peak working set。CSV 另列终止复核前时间与终止复核时间，便于区别主求解与全情景验证负担。

每个完整追索块含 75,810 个整数变量。DE 和主问题总整数变量数为 \(75,810m+4\)，约束数为 \(23,020m+1\)，其中 \(m\) 是所含情景数。主问题的块比例 \(\rho\) 与每轮全枚举追索次数分别报告。期望用途为后续算法基线。历史压力情景的计时只描述本次运行。24、32、64 为可选层级，按冻结 3 GB 单次软内存限制及 16 场景的内存增长，本轮止于必需层级。Phase 3.1 记载的 287,443 条合法轨迹及 38,527 个有效 RHS 属于本次认证范围之外。

## 实测结果

三个 Direct DE 和六个 C&CG 运行的最优值均为 **26,465**。单块初始化首轮界为 \([26465,27050]\)，两个并列最坏情景为 DE_ENGINE_61 和 DE_GEAR_61。按规则只加入 DE_ENGINE_61，第二轮界闭合为 \([26465,26465]\)。双块初始化已经包含 DE_GEAR_61，首轮界闭合，终止时的独立全情景复核仍识别出两个并列最坏情景。三个集合中的两种初始化均以两个完整块结束。不同方法恰好返回相同代表政策 (915,0,0)，成本 915，预算余量 3/19。不同三元组达到同一精确最优值时，审计标为 ALTERNATIVE_ROBUST_OPTIMUM。本轮回归用可枚举的小例验证了这种情况。

| 情景数 | DE 端到端时间 (s) | 单块初始化 (s) | 双块初始化 (s) | DE 峰值 (GiB) | 单块初始化峰值 (GiB) | 双块初始化峰值 (GiB) | 两种 C&CG 的最终块比例 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | 30.07 | 38.43 | 27.95 | 0.587 | 0.348 | 0.328 | 50% |
| 8 | 54.40 | 69.60 | 45.77 | 1.093 | 0.349 | 0.328 | 25% |
| 16 | 114.01 | 127.51 | 85.09 | 2.112 | 0.356 | 0.329 | 12.5% |

最大的 DE 有 1,212,964 个整数变量和 368,321 条约束。两种 C&CG 的最大主问题均有 151,624 个整数变量和 46,041 条约束。单块初始化在每档依次求解两轮全枚举及一轮独立全情景复核，因此用时比 DE 长。双块初始化在每档求解一轮全枚举及一轮独立全情景复核，本次观测用时比 DE 短。三个 DE 及九个主问题的求解状态均为 OPTIMAL。168 次固定政策追索也全部达到 OPTIMAL。180 次求解的日志均已保存，所有求解器及整数矩阵复核的最大残差为 0。

Git HEAD 为 02143f46cab6e6a173a0f495e21b20d21311096f。Python 3.12.7 和 Gurobi 13.0.1 已通过现场求解验证。前序清单共 713 个文件条目核验通过。10 个定向测试模块的 68 个用例通过，含 8 个新增用例。覆盖上下界方向及单调性、同一投资和独立运营块、整数域、重复防护、终止复核、DE 同值及多最优政策。工作在 Phase 3.2A 停止。[pytest](../artifacts/v3_phase32a_20261111_212045/pytest.txt) · [机器可读审计](../artifacts/v3_phase32a_20261111_212045/audit.json) · [SHA-256](../artifacts/v3_phase32a_20261111_212045/sha256_manifest.csv)

## 复现

从仓库根目录运行。依赖 Gurobi 13.0.1、NumPy、psutil、pyxlsb 和 pytest，并提供与 Phase 3.1R 相同的源工作簿 ZIP。运行目录下的日志和 JSON 由本次程序写入；在独立副本中重跑可保留原始归档。

    $env:PYTHONPATH = 'src'
    $run = 'artifacts/v3_phase32a_20261111_212045'
    python -B "$run/run_benchmark.py"
    'python -B -m pytest -vv tests/test_v3_phase32a_plain_ccg.py' | Set-Content -Encoding UTF8 "$run/pytest.txt"
    python -B -m pytest -vv tests/test_v3_phase32a_plain_ccg.py 2>&1 | Out-File -Append -Encoding UTF8 "$run/pytest.txt"
    $testExit = $LASTEXITCODE
    $testExit | Set-Content -Encoding ASCII "$run/pytest_exit_code.txt"
    if ($testExit -ne 0) { exit $testExit }
    python -B "$run/assemble.py"

[逐轮上下界](../artifacts/v3_phase32a_20261111_212045/plain_ccg_iteration_log.csv) · [Direct 比较](../artifacts/v3_phase32a_20261111_212045/plain_ccg_vs_direct_de.csv) · [政策审计](../artifacts/v3_phase32a_20261111_212045/plain_ccg_policy_audit.csv) · [场景使用](../artifacts/v3_phase32a_20261111_212045/plain_ccg_scenario_usage.csv) · [分离记录](../artifacts/v3_phase32a_20261111_212045/plain_ccg_oracle_evaluations.csv) · [精确性证书](../artifacts/v3_phase32a_20261111_212045/plain_ccg_exactness_certificate.json)
