# V3 Phase 3.2D-2R 事件预算修复与多 BOM 复验

**结论** `PASS_EVENT_BUDGET_MULTIBOM_UNCERTAINTY`

## 冻结口径与语义

Git HEAD 为 `02143f46cab6e6a173a0f495e21b20d21311096f`。本轮新增事件预算模块，继续使用 28,000 VIN 的历史开窗、原 BOM、生产与运输能力、三位置保护库存和完整整数追索。运营模型与冻结 BTB 的源文件和前轮证据通过 SHA-256 复核。发动机生产通过 Phase 3.1R 的资源证据筛选，纳入同口径计数。覆盖三项电池资源以及变速箱、座椅、发动机各一项。 [资源身份](../artifacts/v3_phase32d2r_20261112_134524/multibom_risk_resource_catalog.csv) · [机器审计](../artifacts/v3_phase32d2r_20261112_134524/audit.json)

\(\Gamma_{\mathrm{evt}}\in\{1,2,3\}\) 是同一情景的事件数上限，每资源最多一次。\(K=2\) 是每日活跃资源数上限。累计资源日只用于诊断。核心时长 4、7、11，强度 25%、50%、75%，均采用突然恢复。A–E 在目录构造前实际通过。三次 7 日中断可用 61、61、68 的起始日满足 \(K=2\)，将第三次提前至 67 则因三重重叠被拒绝。 [模型和编码](../artifacts/v3_phase32d2r_20261112_134524/event_level_uncertainty_model.md) · [原新口径对照](../artifacts/v3_phase32d2r_20261112_134524/old_vs_new_uncertainty_budget.md) · [语义回归证据](../artifacts/v3_phase32d2r_20261112_134524/event_budget_regression.csv)

## 全集计数

每个资源各有 11 个 4 期起点、8 个 7 期起点和 4 个 11 期起点。乘三个强度得到 69 个原始事件。对给定的三资源组合，23³ 个时段组合中，4,788 个满足 \(K=2\)，分别用位掩码与日期集合独立复核。随后按实际受扰 RHS 去重，计数阶段未构建整数追索模型。

| 事件家族 | Γ=1 合法 / RHS | Γ=2 合法 / RHS | Γ=3 合法 / RHS |
|---|---:|---:|---:|
| B | 207 / 148 | 14,490 / 6,151 | 143,766 / 28,183 |
| G | 69 / 69 | 69 / 69 | 69 / 69 |
| S | 69 / 69 | 69 / 69 | 69 / 69 |
| BG | 0 / 0 | 14,283 / 10,212 | 402,111 / 183,552 |
| BS | 0 / 0 | 14,283 / 10,212 | 402,111 / 183,552 |
| GS | 0 / 0 | 4,761 / 4,761 | 4,761 / 4,761 |
| BGS | 0 / 0 | 0 / 0 | 387,828 / 285,021 |
| Total（含发动机家族及 NR） | **415 / 355** | **71,830 / 51,070** | **2,657,350 / 1,564,150** |

家族按事件所在的 BOM 分支统计，允许 B 同时包含多个不同电池资源。同一个实际 RHS 可能跨事件家族出现，例如电芯事件发生在无收货日期时，含该事件的联合轨迹与去掉它的轨迹完全同效。Total 对跨家族同效类再次去重。目录保存全部类别和每类精确事件数分层的原轨迹重数。独立回归测试从局部签名的全部合法时间候选重新得到全集总数。 [完整计数](../artifacts/v3_phase32d2r_20261112_134524/multibom_scenario_count_by_gamma.csv) · [分支汇总](../artifacts/v3_phase32d2r_20261112_134524/multibom_family_summary.csv) · [起点、时长与强度分布](../artifacts/v3_phase32d2r_20261112_134524/multibom_event_distribution.csv) · [RHS 类目录](../artifacts/v3_phase32d2r_20261112_134524/multibom_effective_rhs_catalog/classes.npz)

## 精确复验与下一阶段门槛

在三个冻结政策各 17 个不同 RHS 上运行完整整数追索，共 51 次。对其中一个联合反例的三个隔离分支另做 42 次整数到期前缀求解。Gurobi 13.0.1 的 93 次求解全部为全局最优，目标等于界，最优间隙及最大整数矩阵复核残差均为 0。三个政策在代表子集的最坏情景均为 `BGS7`，准时交付均为 18,600。固定 \((915,0,0)\) 时，分支最小值和一维到期前缀 DP 均为 21,350，独立损失相加为 17,337，电池递推为 27,363。每个值均基于同一政策和可追溯的完整模型或既有化简。 [MILP 日志与见证索引](../artifacts/v3_phase32d2r_20261112_134524/fixed_policy_full_milp.csv) · [非分离性证书](../artifacts/v3_phase32d2r_20261112_134524/multibom_nonseparability_revalidation.md)

三个政策的冻结 BTB 均得到 17 候选、0 剪枝、17 次单情景 MILP。已冻结的配对规则要求两条同日容量行，核心 4 期起的座椅事件使该规则在完整目录中无适用配对。此结果支持研究后续精确隐式分离。验收覆盖全集组合与 RHS 计数，以及有限代表子集的整数追索。隐式分离、全集追索和全规模 C&CG 均未启动。 [BTB 实测](../artifacts/v3_phase32d2r_20261112_134524/multibom_btb_reaudit.csv) · [准入逐项判定](../artifacts/v3_phase32d2r_20261112_134524/implicit_separation_gate.md)

## 复现

首次目录运行因当前 Python 缺少工作簿解析依赖失败。将项目已声明的 `pyxlsb==1.0.10` 安装到临时目录后重跑成功。Gurobi 使用 1 线程、种子 20261110，三类容差为 \(10^{-9}\)，相对及绝对 MIP gap 为 0。原数据 ZIP 的完整 SHA-256 与路径可从 Phase 3.1R 审计追溯。

在独立副本的仓库根目录运行以下 PowerShell 命令。最后一条需要原始 D-2R 指令文本以复核其哈希。

    $run = 'artifacts/v3_phase32d2r_20261112_134524'
    $phaseDeps = Join-Path $env:TEMP 'prefab-phase32d2r-deps'
    python -m pip install --target $phaseDeps pyxlsb==1.0.10
    $env:PYTHONPATH = "src;$phaseDeps"
    $env:PYTHONIOENCODING = 'utf-8'
    python -B -m pytest -p no:cacheprovider -vv tests/test_v3_phase32d2r_event_budget.py | Tee-Object -FilePath "$run/pytest_semantics.txt"
    $phaseExit = $LASTEXITCODE
    Set-Content "$run/pytest_semantics_exit_code.txt" $phaseExit
    if ($phaseExit -ne 0) { exit $phaseExit }
    python -B "$run/catalog.py"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    python -B "$run/revalidate.py"
    $phaseExit = $LASTEXITCODE
    Set-Content "$run/revalidation_exit_code.txt" $phaseExit
    if ($phaseExit -ne 0) { exit $phaseExit }
    $phaseTests = @(Get-ChildItem tests -Filter 'test_v3*.py' | ForEach-Object { 'tests/' + $_.Name })
    ('python -B -m pytest -p no:cacheprovider -vv ' + ($phaseTests -join ' ')) | Set-Content "$run/pytest_command.txt"
    python -B -m pytest -p no:cacheprovider -vv @phaseTests | Tee-Object -FilePath "$run/pytest.txt"
    $phaseExit = $LASTEXITCODE
    Set-Content "$run/pytest_exit_code.txt" $phaseExit
    if ($phaseExit -ne 0) { exit $phaseExit }
    python -B "$run/assemble.py" '<D-2R 原始指令文本路径>'

[实际 pytest 日志](../artifacts/v3_phase32d2r_20261112_134524/pytest.txt) · [机器审计](../artifacts/v3_phase32d2r_20261112_134524/audit.json) · [SHA-256 清单](../artifacts/v3_phase32d2r_20261112_134524/sha256_manifest.csv)
