# Phase 3.2D-1 全有效 RHS 的 BTB 可扩展性验收

**IMPLICIT_SEPARATION_JUSTIFIED**

认证范围为 Phase 3.1 的历史开窗完整组合候选集，标记为 **STRESS_TEST_ONLY**。保持 28,000 VIN、原嵌套 BOM、正常与在途库存、容量、时序、整数追索和准时交付目标。四个第一阶段政策均为 Phase 3.2P 已认证的代表政策，本阶段固定政策。

## 目录重建与身份

使用冻结的三个电池风险资源，分别为 L1 电芯固定收货、L2 Pack 生产和 L3 Pack 运输。每资源最多一段连续中断，时长 1/3/5 日，强度 25/50/75%，突然恢复，资源日预算 6，每日并发至多 2。用日期集合逐项独立核对了 12,655 个合法支持，映射到 **287,443 条合法轨迹、38,527 个不同有效 RHS**。

对每条轨迹，签名取实际进入模型的电芯固定收货值和两条弧的全部逐日容量。保存有理数原值，如 441/2。对整型流量，容量行下取整得到等价 RHS。实际有理数与整数等价版本均恰有 38,527 类，未发生跨原始 RHS 的合并。每类的代表轨迹都重新调用冻结衰减函数核对实际输入。轨迹映射保存每条轨迹和对应类，类别乘数可由映射重算。严重度、时长、起始日按代表轨迹记录，受影响资源、日期与可达组按有效行计算。[完整 RHS 目录](../artifacts/v3_phase32d1_20261112_111159/full_effective_rhs_catalog.csv) · [轨迹映射](../artifacts/v3_phase32d1_20261112_111159/trajectory_to_rhs_mapping.csv) · [参数键与冻结身份](../artifacts/v3_phase32d1_20261112_111159/catalog_metadata.json)

## 实际 BTB 筛选和时长

Phase 3.2C 的 Pack 到货和座椅 JIT 前缀分别计算，取较小值作安全服务上界。该目录没有受扰座椅容量行，也没有发动机或变速箱冲击，因此没有符合冻结规则的共同整数见证配对。未经单独求解的下界为 0，而各类的安全上界均为正。严格剪枝须有 \(L>w\)，其中 \(w\) 是已精确求解情景中的最小服务；此目录中下界为 0 的候选无法满足该条件。前缀上界用于排序和核验，单凭上界不能排除最坏候选。

| 政策 | 固定库存 \((C,T,O)\) | BOUND_EXACT | SAFE_PRUNED | MILP_REQUIRED | MILPFraction | BTB 首批实跑最坏值 |
|---|---:|---:|---:|---:|---:|---:|
| P1 基准 | (915,0,0) | 0 | 0 | 38,527 | 100% | 27,039 |
| P2 T1 必用环境 | (1338,24,0) | 0 | 0 | 38,527 | 100% | 27,063 |
| P3 强运输混合政策 | (713,135,6) | 0 | 0 | 38,527 | 100% | 27,180 |
| P4 高预算 | (1338,0,162) | 0 | 0 | 38,527 | 100% | 27,201 |

预算点选择沿用 Phase 3.2P 的 BASE_B100、BASE_B150、R3_S75_D7_ABRUPT_B100 和 BASE_B200。按安全上界由低到高、类 ID 打破平局，执行每政策最前 32 个待求类。每次用真实全网 Gurobi 整数最优更新当前最坏值，随后对所有待求类重做严格剪枝判断。128 次重筛均未剪枝。这里把 32 类连续队首批作为扩展成本诊断，余下每个政策的 38,495 个 BTB 待求类仍在清单中。当前部分 incumbent 在 P1 与 P3 上尚未达到真实最坏值。在 P2 与 P4 上，首批命中真实值仍缺少 BTB 全集闭合。

目录生成实测 15.46 秒，四个政策的完整扫描各约 3.00–3.06 秒。每个政策 32 次整数追索的实测总耗时约 41.07–42.27 秒，包含建模、求解与残差检查。按这些实测成本线性外推，逐一求解 38,527 类约 **13.74–14.14 串行小时/政策**。这是基于排序首批的外推，后续类的求解复杂度和负载可能不同。全量 BTB 墙钟时间缺失。该路径需要逐类求完整 MILP，本次扩展审计在确认零压缩后止于初批实跑。加上目录生成和独立认证后的实测阶段时长和为每政策 76.25–79.73 秒，其中目录生成是四个政策共用的一次运行。[分类清单](../artifacts/v3_phase32d1_20261112_111159/full_rhs_bound_classification.csv) · [逐步 incumbent](../artifacts/v3_phase32d1_20261112_111159/full_rhs_incumbent_updates.csv) · [实测与外推](../artifacts/v3_phase32d1_20261112_111159/full_rhs_runtime_breakdown.csv)

## 独立全集最坏值与整数可行性

参考路径沿用 Phase 3.1 已证明的历史纯服务化简。首先逐期复核能服务全体非电池零部件需求的完整冻结 JIT 见证。三类电芯由固定供给进入，再分别经历一期加工、一期运输。累计加工、发运和 Pack 到货的逐期极大序列由整数物料守恒与容量给出，按到期日分配 Pack 取得 BEV 服务上界。结合非电池见证即为完整全网追索值。对每个政策逐一评价全部 38,527 类，不把参考值用于 BTB 的排序、剪枝或停止。

| 政策 | 全目录精确最坏交付 | 并列最坏 RHS 类 | 原矩阵整数见证复验 |
|---|---:|---:|---:|
| P1 | **26,652** | 4,942 | 4,942 |
| P2 | **27,063** | 101 | 101 |
| P3 | **26,591** | 4,942 | 4,942 |
| P4 | **27,201** | 101 | 101 |

全部 154,108 个政策—RHS 的独立值均落在现有 BTB 上下界内。128 次排序首批的全网整数最优与独立参考逐项一致。另对每个政策的首个并列最坏类运行一次完整 MILP，均为零间隙且与参考最坏值一致。对 **全部 10,086 个最坏政策—RHS 对** 构造整数方案，使用完整约束矩阵核对变量界、库存递推、需求平衡和容量，最大矩阵残差为 **0**。同一政策、同一流量与固定收货可共用矩阵运算，改变的实际容量行对每个类另行核对。这是对全集最坏值和并列集合的独立精确认证。BTB 首批的目标只在其中两政策命中，全集 BTB 精确闭合未执行。[最坏值证书及并列清单](../artifacts/v3_phase32d1_20261112_111159/full_rhs_worst_case_certificate.csv) · [全部并列项矩阵复验](../artifacts/v3_phase32d1_20261112_111159/reference_tie_matrix_replay.csv) · [实际 MILP 调用](../artifacts/v3_phase32d1_20261112_111159/full_rhs_solver_calls.csv)

## 结构与准入

38,526 类存在有效电池风险，另有一个名义等效 RHS。一个、两个、三个电池层有效受扰分别有 222、9,900、28,404 类，均位于电池 BOM 分支。截止日前可达的 VIN 配置、实际容量行、并发期和 BOM 深度在清单中逐类记录。所有有候选的强度、时长、起点及到期覆盖组均需要完整 BTB 追索。变速箱、座椅和跨 BOM 联合风险没有候选，筛选率无定义。现有 3.2C 筛选收益依赖座椅 JIT 相容配对，在该完整候选集上没有对应结构。

若继续用同一全整数追索 oracle 覆盖大规模组合集，显式 BTB 的 100% MILP 需求支持研究不依赖逐类完整求解的分离。对本历史电池专用模型，已冻结的精确参考本身已在每个政策约 13 秒完成全部类别，因此本轮不构成一般多 BOM 网络必须使用隐式分离的证据。工作止于 D-1 证据验收。现实风险校准仍待解决。[机制准入](../artifacts/v3_phase32d1_20261112_111159/implicit_separation_gate.md) · [风险统计](../artifacts/v3_phase32d1_20261112_111159/full_rhs_risk_family_analysis.csv) · [MILP 需求及 BOM 时序](../artifacts/v3_phase32d1_20261112_111159/full_rhs_milp_required.csv)

## 复现与记录

Git HEAD 为 02143f46cab6e6a173a0f495e21b20d21311096f。使用 Gurobi 13.0.1、单线程/模型、默认 presolve、容差 \(10^{-9}\) 及零绝对和相对 MIPGap。132 次完整追索日志保留在本阶段目录，最大求解器残差为 0。97 项定向回归通过，其中新增 5 项。初次目录预检把 12,655 的数字抄成 12,565，发现后将断言绑定到冻结审计计数。两种生成方式的支持集合相同，原参数和代码保持原值。

从独立副本的仓库根目录运行，需同一源 ZIP、Python、Gurobi、NumPy、pyxlsb 和 pytest。

    $env:PYTHONPATH = 'src'
    $run = 'artifacts/v3_phase32d1_20261112_111159'
    python -B "$run/catalog_d1.py"
    python -B "$run/run_d1.py" all
    python -B "$run/replay_ties.py"
    python -B "$run/assemble.py"
    'python -B -m pytest -vv tests/test_v3_phase32d1_full_rhs.py' | Set-Content -Encoding UTF8 "$run/pytest.txt"
    python -B -m pytest -vv tests/test_v3_phase32d1_full_rhs.py 2>&1 | Out-File -Append -Encoding UTF8 "$run/pytest.txt"
    $testExit = $LASTEXITCODE
    $testExit | Set-Content -Encoding ASCII "$run/pytest_exit_code.txt"
    if ($testExit -ne 0) { exit $testExit }
    python -B "$run/assemble.py"

[机器可读审计](../artifacts/v3_phase32d1_20261112_111159/audit.json) · [测试输出](../artifacts/v3_phase32d1_20261112_111159/pytest.txt) · [SHA-256 清单](../artifacts/v3_phase32d1_20261112_111159/sha256_manifest.csv)
