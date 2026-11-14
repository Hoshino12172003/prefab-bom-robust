# prefab-bom-robust

多层级供给风险、嵌套 BOM 与缓冲库存研究。公开分支记录 V1 至 V3 的模型、求解和审计证据。

- [V2.5 Phase 1 认证](docs/v25_phase1_formal_certification.md)
- [V3 Phase 3.2D4 完整 C&CG 结果](docs/v3_phase32d4_full_implicit_ccg.md)
- [11,775 辆的根因](docs/v3_phase32d4_11775_root_cause_audit.md)
- [全 BOM 与 91 个候选位置审计](docs/v3_full_bom_four_audits.md)
- [Seat OEM 预置诊断](audit/v3_seat_oem_preposition_diagnostic.md)
- [公开归档和本地版本映射](docs/public_release.md)

## 早期模型与 V1 验证

V2.1 动态模型位于 `src/prefab_v21/`。执行 `python -m examples.run_v21` 可实际运行 Gurobi 基础认证、门槛检查和微型 A0/A1/A2/A3 配对。运行产物进入独立时间戳目录。最近的结果是基础 `PASS_V2_BASE_EXACT`、割有效性 `PASS_V2_CUT_VALID`，算法效果 `PARTIAL_V2`。详见 [V2.1验收报告](docs/v21_exact_baseline_report.md)。

第二篇期刊论文的 V1 多层级供给风险 BOM 交付模型。以下保留 V1 微型验证的运行说明。

## 环境

- Python 3.10+
- Gurobi / `gurobipy`（必须有可用许可证）
- pytest

```powershell
python -m pip install -e ".[test]"
python -m compileall -q src tests examples
python -m pytest -q
python examples\run_examples.py
python -m examples.run_acceptance
```

不安装包时，测试仍会通过 `pyproject.toml` 中的 `pythonpath=src` 找到源码；示例脚本也会显式加入本项目的 `src`，不会依赖当前目录之外的代码。

## 精确性边界

`solve_direct` 同时展开 T2、T3 连续预算集合的全部极点；`solve_ccg` 的分离子问题也遍历同一完整极点集。因此只有在极点总数不超过安全阈值且每个 Gurobi 模型取得 `OPTIMAL` 时，才报告小规模精确认证。超过阈值会停止并报告“当前没有可用的精确最坏情景认证方法”，不会退化为启发式认证。

两个可人工核验算例位于 `src/prefab_bom_robust/examples.py`，运行入口为 `examples/run_examples.py`。验收入口额外运行独立 Gurobi 投影模型和三产品族案例，输出每个极点的残差及交付量、上下界和 C&CG 迭代。最近一次实际执行的证据见 [V1 正确性验收报告](docs/v1_acceptance_report.md)。

## 目录

- `src/prefab_bom_robust/data.py`：数据结构与物理一致性校验
- `src/prefab_bom_robust/uncertainty.py`：预算集合极点与阈值保护
- `src/prefab_bom_robust/solvers.py`：名义、Phase-I、直接展开、C&CG
- `tests/test_v1.py`：T01—T16 自动化验证
- `docs/`：数学模型、审计和精确验证记录


