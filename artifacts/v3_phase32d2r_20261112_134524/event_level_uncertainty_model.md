# 事件级不确定集

每个合法事件 \(e=(r,\tau,d,s,h)\) 由真实资源 \(r\)、开始期 \(\tau\)、时长 \(d\)、损失比例 \(s\) 和恢复类别 \(h\) 确定。事件覆盖 \(\tau,\ldots,\tau+d-1\)，须完整落在第 61–74 期。固定 \(h=\texttt{ABRUPT\_RECOVERY}\)，活跃期剩余可用比例为 \(1-s\)，结束后恢复为 1。

$$
\begin{aligned}
&y_e\in\{0,1\},\quad
\sum_e y_e\le\Gamma_{\mathrm{evt}},\quad
\sum_{e:r(e)=r} y_e\le1\quad(\forall r),\\
&z_{rt}=\sum_{e:r(e)=r,\,\tau_e\le t<\tau_e+d_e}y_e,\quad
\sum_r z_{rt}\le K=2\quad(\forall t),\\
& E=\sum_{r,t}z_{rt}=\sum_e d_e y_e\quad\text{仅记录。}
\end{aligned}
$$

\(\Gamma_{\rm evt}\in\{1,2,3\}\) 是 14 期情景内可选择的事件数上限。每资源最多一个事件，因而也限制该情景所包含的受扰资源数。\(K=2\) 则是同一日活跃资源数上限。两个值均为模型设计，事件预算标为 `ROBUSTNESS_SENSITIVITY`。强度 25%、50%、75% 和时长 4、7、11 标为 `STANDARDIZED_STRESS_LEVEL`，时长档沿用 D-2 外部事件量级说明。核心全集只含突然恢复，不纳入 100% 损失。既有渐进尾部保留在原电池实现中，完整多分支没有冻结的渐进映射，本轮未另计。 [前轮外部证据与适用边界](../../docs/v3_phase32d2_multibom_uncertainty_calibration.md)

对电池电芯收货按 SKU 与日期取 \(\lfloor q^N_{pt}(1-s)\rfloor\)。对 Pack 生产、Pack 运输、变速箱运输、座椅 JIT 配送和发动机生产，沿用 Phase 3.1R 同日弧容量行 \(\lfloor C_{rt}(1-s)\rfloor\)。事件变量只用于定义不确定集，运营模型仍由原完整整数追索接收固定 RHS。资源坐标和证据逐项登记。 [资源目录](multibom_risk_resource_catalog.csv)

## 精确去重口径

每个资源的局部向量包含它可改变的全部行，分别是电芯固定收货的 6 行和 5 条弧各 14 个容量行。向量位置按资源、行类型和键固定。各组坐标不相交，其余模型矩阵和 RHS 固定。组合类用六个 7 位局部 ID 打包，0 代表该组名义向量，数值按实际整数 RHS 比较。完全相同的 RHS 共享类 ID，交付值未参与去重。电芯收货日期稀疏，存在 15 个完全无效的电芯事件及若干同效区间。原轨迹的并发约束必须在去重前检查。

`multibom_effective_rhs_catalog/classes.npz` 保存升序的 `ids`，以及按恰好 0、1、2、3 个事件分层的 `exact_event_count_multiplicity`。第 \(i\) 个资源的局部 ID 为 `(id >> (7*i)) & 127`。在同目录 `rhs_coordinates.json` 查行键和对应向量。对 \(\Gamma_{\rm evt}=g\) 汇总第 0 至 g 层，和为正的类属于该预算。若要恢复合法原轨迹，对每个局部 ID 取对应选项，对所有候选轨迹应用事件预算和每日并发。可恢复无效事件的成员资格。CSV 的事件家族由原事件分支定义，有效家族由非零 RHS 坐标定义。只有后一口径的各家族 RHS 类可直接相加。 [完整类别目录](multibom_effective_rhs_catalog/classes.npz) · [解码坐标](multibom_effective_rhs_catalog/rhs_coordinates.json) · [家族口径](multibom_family_summary.csv)
