# V3 Phase 3.2D-4 完整隐式事件空间 C&CG

**验收状态** `INCONCLUSIVE_PHASE32D4`。三档完整鲁棒 C&CG 与完整 Direct DE 最优值的独立数学证书均闭合。第 5 项要求的 355 块单体 Gurobi 运行未取得 `OPTIMAL`。

## 口径和界

沿用 Phase 3.2A 的成本 \((1,27/19,297/190)\) 与预算 \(17388/19\)。历史开盘、28,000 VIN、原嵌套 BOM、三类整数缓冲、完整整数追索，以及 D-2R 的事件定义和每日并发 \(K=2\) 保持冻结。每轮主问题调用 Phase 3.2A 的共享投资与完整整数场景块，事件分离直接调用 D-3 的搜索、包络和精确缓存。新增的外层循环只负责连接两者，沿用 \(10^{-6}\) 绝对界差阈值。

主问题最大化保证服务量，精确目标值给出 \(UB_k\)。固定主问题政策后，仅接受合法最坏情景已验证、搜索前沿为空且上下界闭合的 oracle 结果。历轮已认证政策的最高保证量给出 \(LB_k\)。若界未闭合，加入严格违反的最坏情景块。同一有效 RHS 以相同标识去重。终止后从新求解器模型复验保留政策。

## 完整鲁棒求解

| Γ_evt | 合法轨迹 | 有效 RHS | 最优准时交付 | 代表政策 | 最终界差 | 外层和终止 oracle 秒 |
|---:|---:|---:|---:|---|---:|---:|
| 1 | 415 | 355 | 11,775 | (915,0,0) | 0 | 68.47 |
| 2 | 71,830 | 51,070 | 11,775 | (915,0,0) | 0 | 23.52 |
| 3 | 2,657,350 | 1,564,150 | 11,775 | (915,0,0) | 0 | 23.59 |

三档的第一轮界均为 [11,775, 27,363]，第二轮界均为 [11,775, 11,775]。主问题块从名义情景一个增加到名义加座椅中断两个。Γ=2 和 Γ=3 每次 oracle 各调用两次合法情景 MILP、四次包络 MILP。各自的终止政策通过 414 个根分支的独立完整矩阵重放，分别覆盖 71,830 和 2,657,350 条合法轨迹，矩阵残差为 0。Γ=1 终止政策的 355 个 RHS 均逐项求解，匹配全部四个并列最坏 RHS。Γ=2 和 Γ=3 的证书覆盖完整最坏值和合法最坏事件代表。 [迭代、耗时与内存](../artifacts/v3_phase32d4_20261112_191057/full_implicit_ccg_iteration_log.csv) · [工作量](../artifacts/v3_phase32d4_20261112_191057/implicit_ccg_workload.csv) · [独立证书](../artifacts/v3_phase32d4_20261112_191057/final_policy_independent_certificate.json)

## 最坏风险与缓冲政策

三个代表情景共用实际 RHS `16106127360`。座椅 JIT 配送在第 61–71 期损失 75%，随后立即恢复。受扰时该弧容量为 525 件/期，在三个代表整数见证中均满载。所有 1,286 个 VIN 分组、28,000 辆订单的 BOM 均需一件座椅。四类座椅按 SKU 在 OEM 零库存约束下配料，逐日收货等于对应装配耗用。到期累计上界在第 71–74 期取到 11,775。Γ=2 和 Γ=3 的代表还含一个电芯事件，其受扰日期没有相应固定到货，产生零条实际 RHS 变化。 [事件与风险暴露](../artifacts/v3_phase32d4_20261112_191057/gamma_worst_event_comparison.csv) · [容量见证](../artifacts/v3_phase32d4_20261112_191057/binding_capacity_rows.csv) · [座椅 BOM 见证](../artifacts/v3_phase32d4_20261112_191057/binding_bom_components.csv) · [分组交付与缺口](../artifacts/v3_phase32d4_20261112_191057/affected_vin_groups.csv)

Γ=3 的零缓冲政策通过独立全域证书，同样保证 11,775 辆。对任何预算可行政策，将额外库存留在其注入节点，保留零政策追索中的流量和交付。逐 SKU 的开盘、固定收货、可进入窗口的供应上界和预算内最大新增量之和满足库存界。因此所有可行投资均能复用该保证。座椅上界独立于三种电池缓冲，故共同的联合最优集合为

$$
\left\{(x_C,x_T,x_O)\in\mathbb Z_+^3:
190x_C+270x_T+297x_O\le173880\right\}.
$$

集合共有 57,884,083 个整数政策。Γ=3 六次坐标极值优化得到 \([0,915]\)、\([0,644]\)、\([0,585]\)。三个最大值受共同预算约束。结合预算集合嵌套和同一座椅上界，结论也覆盖 Γ=1、2。三档的最优服务率均为 42.0536%。代表政策支出 915、剩余 3/19，零政策同样最优。因此本轮结果不支持随 Γ 增加而恶化、转向下游或增加组合多样性。数据支持的是该压力窗口内座椅瓶颈使电池缓冲失去最坏服务目标上的边际作用。 [联合政策证书](../artifacts/v3_phase32d4_20261112_191057/policy_flatness_certificate.json) · [极值三元组与求解日志](../artifacts/v3_phase32d4_20261112_191057/gamma_policy_set_audit.csv)

## Γ=1 Direct DE 与同域基准

355 块 Direct DE 的实际模型为 26,912,554 个整数列、8,172,101 行及 77,422,663 个非零系数。流式 MPS 以冻结追索块及独立目标联结构造。两块试件逐项对比 Gurobi API 直接建模，矩阵系数、RHS、变量界、变量类型和目标均一致。初始导出发现不出现在约束中的固定零列，随后在 MPS 中显式保留这些列，并改用相对路径读取。完整 MPS 和完整 MIP start 都保留 SHA-256。

独立 Direct DE 数学认证通过。355 个独立追索向量在共享政策 `(915,0,0)` 和 \(\eta=11775\) 下逐块复核原矩阵，提供可行下界。独立建模的座椅最坏块全局最优为 11,775，且该块属于完整 DE，因此提供完整 DE 上界。冻结座椅前缀也给出同一上界。这一证据与外层迭代独立。单体求解器运行状态单独列在交叉核对表。 [Direct DE 交叉核对](../artifacts/v3_phase32d4_20261112_191057/gamma1_direct_crosscheck.csv) · [独立上下界证书](../artifacts/v3_phase32d4_20261112_191057/gamma1_de/bound_certificate.json) · [Gurobi MPS 格式](https://docs.gurobi.com/projects/optimizer/en/current/reference/fileformats/modelformats.html) · [Gurobi CLI](https://docs.gurobi.com/projects/optimizer/en/current/reference/misc/commandline.html)

三次单体运行均接受 11,775 的起点。前两次报告 Gurobi 10001 内存错误。第三次以内存上限结束，峰值工作集约 14.09 GB，保存了 incumbent，但求解器未给出目标界。第三次返回的完整解也按 355 块重放。独立数学界差为 0，单体求解器的最优状态仍缺失。 [首轮日志](../artifacts/v3_phase32d4_20261112_191057/gamma1_de/console.log) · [第二轮日志](../artifacts/v3_phase32d4_20261112_191057/gamma1_de/memory_retry/console.log) · [第三轮日志](../artifacts/v3_phase32d4_20261112_191057/gamma1_de/conservative_retry/console.log)

同域方法对照使用 D-3 的冻结 Γ=2、N=32 子空间和相同成本、预算、整数追索。四种方法都得到 12,300，Direct DE 的代表政策为 (105,0,0)，三种 C&CG 的代表政策为 (915,0,0)。

| 方法 | 迭代分离 MILP | 终止复核 MILP | 总时间（秒） |
|---|---:|---:|---:|
| Direct DE（另求 32 块单体） | 0 | 32 | 120.58 |
| Plain finite C&CG | 64 | 32 | 84.71 |
| BTB finite C&CG | 64 | 32 | 84.61 |
| Implicit Event-Space C&CG | 8 | 4 | 22.11 |

计时只描述本轮机器条件，完整 Γ 域与该子空间之间无直接加速比。BTB 保留为有限情景辅助。 [同域方法对照](../artifacts/v3_phase32d4_20261112_191057/finite_matched_comparison.csv)

## 复现

在仓库根目录运行，设置 `PYTHONPATH` 包含 `src` 和已固定的 pyxlsb 1.0.10。使用 Python 3.12.7 与 Gurobi 13.0.1。模型目标、可行性与整数容差沿用冻结的单线程配置。单体 DE 重试只改 Gurobi 的内存与预求解参数。各命令和退出记录保存在新运行目录。

    $run = 'artifacts/v3_phase32d4_20261112_191057'
    python -B "$run/run.py" preflight
    foreach ($g in 1,2,3) { python -B "$run/run.py" outer $g }
    python -B "$run/gamma1_reference.py"
    python -B "$run/certify.py"
    python -B "$run/interpret.py"
    python -B "$run/direct_de.py" build
    python -B "$run/direct_de.py" solve
    python -B "$run/direct_de.py" memory_retry
    python -B "$run/direct_de.py" conservative_retry
    python -B "$run/direct_bound.py"
    foreach ($m in 'Direct','Plain','BTB','Implicit') { python -B "$run/finite_compare.py" $m }
    $phaseTests = @(Get-ChildItem tests -Filter 'test_v3*.py' | ForEach-Object { 'tests/' + $_.Name })
    python -B -m pytest -p no:cacheprovider -vv @phaseTests 2>&1 | Tee-Object "$run/pytest.txt"
    $rc = $LASTEXITCODE
    Set-Content "$run/pytest_exit_code.txt" $rc
    if ($rc -ne 0) { exit $rc }
    python -B "$run/assemble.py" '<D-4 原始指令文本路径>'

103 项 V3 回归全部通过。汇总程序核查各运行退出记录、证书、测试日志并生成清单。

[机器审计](../artifacts/v3_phase32d4_20261112_191057/audit.json) · [精确性证书](../artifacts/v3_phase32d4_20261112_191057/implicit_ccg_exactness_certificate.json) · [回归测试](../artifacts/v3_phase32d4_20261112_191057/pytest.txt) · [SHA-256 清单](../artifacts/v3_phase32d4_20261112_191057/sha256_manifest.csv)
