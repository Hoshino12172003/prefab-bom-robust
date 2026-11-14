# V3 Phase 3.2D-3 精确事件空间分离原型

**结论** `PASS_IMPLICIT_EVENT_SEPARATION_EXACT_PROTOTYPE`

验收范围是冻结历史压力集下的固定政策整数追索。使用 28,000 VIN、原嵌套 BOM、6 个既有风险资源、事件时长 4/7/11 期、强度 25%/50%/75%、突然恢复和每日并发 2。Git HEAD 为 `02143f46cab6e6a173a0f495e21b20d21311096f`。外层 C&CG 未运行。

## 精确性与证据

414 个原子保留各自的时间支持，包含 354 个非名义 RHS 和 1 个名义等效 RHS。编号 7 和 10 的电芯事件具有相同单事件 RHS，与同一组变速箱和座椅事件组合时，一个合法、一个违反并发。对 28,152 个同资源有序替换进行检查，645 个满足支配替换条件，其中 507 个在至少一行上更不利。搜索中未按支配关系删除原子。 [原子目录](../artifacts/v3_phase32d3_20261112_171131/atomic_event_catalog.csv) · [支配审计](../artifacts/v3_phase32d3_20261112_171131/event_dominance_audit.csv) · [并发反例及库存余量](../artifacts/v3_phase32d3_20261112_171131/mapping_audit.json)

中断包络逐坐标取最不利的可用量或容量。容量均作用于上界行。电芯收货作用于库存等式，需要用恢复的累计来料修正库存。四个政策都通过储存上界检查。全部剪枝均由精确包络值或可在该包络下重放的整数方案认证。Γ=1 采用严格剪枝保留并列。Γ=2/3 的验收目标为最坏值。冻结 BTB 仅用于种子排序和避免无希望的包络调用，归档角色为 `BTB_NOT_PRIMARY_FULL_SET_MECHANISM`。 [搜索树定义](../artifacts/v3_phase32d3_20261112_171131/event_search_tree_definition.md) · [安全下界证明](../artifacts/v3_phase32d3_20261112_171131/event_envelope_bound_proof.md)

| 对照 | 完成情况 | 证据 |
|---|---|---|
| Γ=1，N=355 | 四个政策各逐项求解 355 次，原型各用 24–25 次完整 MILP。全部匹配最坏值 11,775 和四个并列最坏 RHS | [逐政策对照](../artifacts/v3_phase32d3_20261112_171131/implicit_vs_enumeration_gamma1.csv) |
| Γ=2，N=32/64/128/256/512 | 四个政策共 20 组，最坏值全部匹配 | [阶梯对照](../artifacts/v3_phase32d3_20261112_171131/implicit_vs_enumeration_gamma2.csv) |
| Γ=3，N=64/128/256/512/1024 | 四个政策共 20 组，最坏值全部匹配。N=1024 时，原型各用 7 次完整 MILP，平面显式参照用 63–95 次，其余类完成整数矩阵见证重放 | [阶梯对照](../artifacts/v3_phase32d3_20261112_171131/implicit_vs_enumeration_gamma3_subsets.csv) |
| Level 0/1/2 | P1 在 Γ=2 N=32 上分别用 32、15、4 次完整 MILP，在 Γ=3 N=64 上分别用 64、15、5 次。两个测试的三档最坏值均为 12,300 | [调用和节点统计](../artifacts/v3_phase32d3_20261112_171131/implicit_scalability_summary.csv) |

Γ=2/3 阶梯的平面参照遍历每一个冻结 RHS。它对无法用当前可行整数方案证明下界的类求完整最优。其余类逐个重放 23,019 行完整矩阵，证明其目标下界不低于最终最坏值。P1 的 Γ=2 N=32 和 Γ=3 N=64 另做逐项完整 MILP，结果一致。较大阶梯参照认证的是最小值，未报告每类的精确最优值或完整最坏并列集。各阶梯按冻结资源和错峰 7 期设计确定。每档 Γ=3 含必须三个事件才产生的 RHS。 [阶梯定义和家族分布](../artifacts/v3_phase32d3_20261112_171131/benchmark_design.json)

## Γ=3 全空间认证

每个政策的搜索访问 415 个节点，剪枝 414 个一级分支。每政策 2 次合法追索和 4 次包络 MILP，均达到 Gurobi 全局最优并通过矩阵检查。包含包络调用的 EvaluationFraction 为 \(6/1{,}564{,}150\approx3.836\times10^{-6}\)。搜索阶段实测 5.72–6.47 秒，包含种子选择、搜索和求解，不含源文件装载和固定矩阵初始化。进程峰值工作集为 224–227 MB。各政策的完整搜索上限为 2,500 节点、64 次合法追索、8 次包络调用、160 秒。四个前沿均为空。 [逐政策结果](../artifacts/v3_phase32d3_20261112_171131/implicit_policy_comparison.csv)

独立路径重新计算每个一级分支的合法轨迹计数和人工包络。按第一个原子事件分组的 414 个分支加名义情景，精确覆盖 2,657,350 条轨迹。每政策新建完整整数模型并复求六份证书方案，再在 414 个包络上逐一重放完整矩阵，全部残差为零。每个分支均有至少 11,775 辆的可行整数服务证书，一个合法场景达到 11,775。因此对四个政策，Γ=3 全空间下界和上界都等于 **11,775**。认证最坏值和一个合法最坏事件集合，未认证 Γ=3 的全部并列 RHS。 [独立全域覆盖与复求](../artifacts/v3_phase32d3_20261112_171131/full_independent_certificate.json) · [P1 逐分支重放](../artifacts/v3_phase32d3_20261112_171131/independent_full/P1/root_branch_matrix_replay.csv)

Γ=1 与 Γ=3 的全域值相等，且三套事件预算集合嵌套，因此 Γ=2 全域最坏值也为 11,775。可选的 51,070 类逐项全域参考未运行。代表最坏 RHS 对应座椅配送在 61–71 期损失 75%，种子中的另一电芯事件在实际 RHS 上无效。结果说明这个冻结压力集和这四个政策可通过少量包络证书闭合，不能据此推断其他网络、预算或政策有相同剪枝率。 [精确性证书](../artifacts/v3_phase32d3_20261112_171131/implicit_exactness_certificate.json)

## 复现

使用 Python 3.12.7、Gurobi 13.0.1、NumPy、SciPy、psutil、pytest 和项目固定的 pyxlsb 1.0.10。整数求解为单线程、种子 20261110，最优性、可行性和整数容差均为 \(10^{-9}\)，相对和绝对 MIP gap 为 0。独立参考与搜索采用同一物理模型、政策和情景定义。墙钟计时来自实际并行实验，峰值内存为各进程到当前点的工作集峰值。

从独立副本仓库根目录执行。下列阶段应按顺序执行并检查各阶段退出码。

    $run = 'artifacts/v3_phase32d3_20261112_171131'
    $phaseDeps = Join-Path $env:TEMP 'prefab-phase32d2r-deps'
    $env:PYTHONPATH = "src;$phaseDeps"
    $env:PYTHONIOENCODING = 'utf-8'
    python -B "$run/prepare.py"
    python -B "$run/audit_mapping.py"
    python -B "$run/batch.py" --workers 8 reference:gamma1:P1 reference:gamma1:P2 reference:gamma1:P3 reference:gamma1:P4 implicit:gamma1:P1 implicit:gamma1:P2 implicit:gamma1:P3 implicit:gamma1:P4
    python -B "$run/gamma1_gate.py"
    python -B "$run/batch.py" --workers 8 reference:ladder:P1 reference:ladder:P2 reference:ladder:P3 reference:ladder:P4 implicit:ladder:P1 implicit:ladder:P2 implicit:ladder:P3 implicit:ladder:P4 implicit:levels:P1 implicit:full:P1 implicit:full:P2 implicit:full:P3 implicit:full:P4
    python -B "$run/batch.py" --workers 1 reference:pointwise_small:P1
    python -B "$run/replay_search.py"
    python -B "$run/verify_full.py"
    $phaseTests = @(Get-ChildItem tests -Filter 'test_v3*.py' | ForEach-Object { 'tests/' + $_.Name })
    python -B -m pytest -p no:cacheprovider -vv @phaseTests 2>&1 | Tee-Object "$run/pytest.txt"
    $phaseExit = $LASTEXITCODE
    Set-Content "$run/pytest_exit_code.txt" $phaseExit
    if ($phaseExit -ne 0) { exit $phaseExit }
    python -B "$run/assemble.py" '<D-3 原始指令文本路径>'

[Gurobi 运行及节点索引](../artifacts/v3_phase32d3_20261112_171131/implicit_search_iteration_log.csv) · [回归日志](../artifacts/v3_phase32d3_20261112_171131/pytest.txt) · [机器审计](../artifacts/v3_phase32d3_20261112_171131/audit.json) · [SHA-256 清单](../artifacts/v3_phase32d3_20261112_171131/sha256_manifest.csv)
