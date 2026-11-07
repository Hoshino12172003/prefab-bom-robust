# V1 数学模型

## 1. 时序、集合与口径

第一阶段在风险发生前选择新增组件库存 (x_j\ge0)、备用协议 (y_k\in\{0,1\}) 和独立备用资源预留量 (r_k\ge0)。风险 ω=(η,ξ) 实现后，连续追索变量为 T2 组件交付 (q_{sj})、T3 正常/备用分配 (t_{ks},g_{ks})、产品完成/未完成量 (w_m,u_m)。每个场景有自己的一套追索变量，但共享同一个 (x,y,r)。

集合和参数沿用任务定义。实现中 `family[m]` 表示 (m\in M_h)，`pool_node[k]` 表示 (v(k))。只为 ((s,j)\in E)、((k,s)\in N)、((k,s)\in B_{arc}) 创建相应流变量。(B_{arc}\subseteq N)。每个 (b_{ksj}>0) 必须同时有 ((s,j)\in E) 与 ((k,s)\in N)。不同物理资源池在不同的 (k) 约束中分别守恒，不作无转换规则的加总。

## 2. 第一阶段

投资成本

\[
C^{pre}(x,y,r)=\sum_j c^I_jx_j+\sum_k(f_ky_k+c^R_kr_k).
\]

约束为

\[
0\le x_j\le \bar X_j,\qquad 0\le r_k\le \bar R_ky_k,
\]

\[
C^{pre}(x,y,r)\le B_{pre}.
\]

新增库存成本只在 (C^{pre}) 中出现一次；期初库存 (I^0) 不计历史成本。

## 3. 连续预算不确定集

\[
\mathcal U_2=\{\eta\in[0,1]^{|S|}:\sum_s\eta_s\le\Gamma_2\},\quad
\mathcal U_3=\{\xi\in[0,1]^{|V|}:\sum_v\xi_v\le\Gamma_3\}.
\]

可用 T2 产能为 ̅(K_s(1-ε_sη_s))，资源池 (k) 的正常能力为 ̅(C_k(1-δ_kξ_{v(k)}))。实现要求 (0\le\Gamma_2\le|S|)、(0\le\Gamma_3\le|V|)。

## 4. 场景追索约束

对固定 ((x,y,r)) 与 ω：

\[
\sum_{j:(s,j)\in E}a_{sj}q_{sj}\le \bar K_s(1-\epsilon_s\eta_s),\quad\forall s,
\]

\[
\sum_{s:(k,s)\in N}t_{ks}\le \bar C_k(1-\delta_k\xi_{v(k)}),\quad\forall k,
\]

\[
\sum_{s:(k,s)\in B_{arc}}g_{ks}\le r_k,
\qquad
\sum_{s:(k,s)\in B_{arc}}g_{ks}\le \bar C_k\delta_k\xi_{v(k)},\quad\forall k.
\]

第二个备用约束是 V1 的“只替代当期主供应损失”业务假设。

\[
\sum_{j:(s,j)\in E}b_{ksj}q_{sj}\le t_{ks}+\mathbf{1}_{(k,s)\in B_{arc}}g_{ks},\quad\forall(k,s)\in N,
\]

\[
\sum_m A_{jm}w_m\le I^0_j+x_j+\sum_{s:(s,j)\in E}q_{sj},\quad\forall j,
\]

\[
\sum_m\tau_mw_m\le P,\qquad w_m+u_m=D_m\quad\forall m,
\]

\[
\sum_{(s,j)\in E}c^Q_{sj}q_{sj}+\sum_{(k,s)\in B_{arc}}c^A_{ks}g_{ks}\le E_{op},
\]

\[
\sum_{m\in M_h}w_m\ge\alpha_h\sum_{m\in M_h}D_m,\quad\forall h.
\]

最后一组约束与所有流约束在同一个场景、同一个 LP 中同时成立，不能按产品族分别求解后拼接。

## 5. 名义目标

名义场景取 η=0、ξ=0，强制 (w_m=D_m)，并固定 (g=0)。令其最小正常采购成本为 (Q^N(x))。主目标为

\[
\min_{x,y,r}\ C^{pre}(x,y,r)+Q^N(x).
\]

名义采购成本只含 (c^Qq)；新增库存已在第一阶段计费，不重复进入 (Q^N)。名义方案与各风险场景方案相互独立。

## 6. Phase-I 与鲁棒判定

将各族服务约束改为

\[
\sum_{m\in M_h}w_m+\sigma_h\ge\alpha_h\sum_{m\in M_h}D_m,qquad\sigma_h\ge0,
\]

并定义

\[
\Phi(z,ω)=\min\sum_h\sigma_h,\qquad
\Psi(z)=\max_{ω\in\mathcal U_2\times\mathcal U_3}\Phi(z,ω).
\]

Phase-I 始终可行：取所有流和 (w) 为 0，(u=D)，(σ_h=α_h\sum_{m\in M_h}D_m)。目标因 σ≥0 有下界，需求有限又给出有限上界，故有界。由于所有 σ 非负，(Φ=0) 当且仅当存在一套追索方案同时满足所有产品族服务约束。因此在精确算术下，(Ψ=0) 等价于鲁棒可行；实现用 (10^{-7}) 作为服务缺口认证容差，并单独报告约束残差。

## 7. 精确极点论证

风险只仿射进入 LP 约束右端，包括“备用不超过损失”约束。固定第一阶段后，Phase-I 最优值可由 LP 对偶写成若干关于 ω 的仿射函数之上确界，因此 Φ 关于 ω 为凸函数。紧致多面体上凸函数的最大值至少在某个极点取得，故完整极点枚举可精确认证最坏值。

对 (\{z\in[0,1]^n:\sum z_i\le\Gamma\})：整数 Γ 的全部极点为至多 Γ 个 1 的二元向量；非整数 Γ 除这些点外，还包含恰有 ⌊Γ⌋ 个 1 和一个值为 Γ−⌊Γ⌋ 的分数分量。因而整数 Γ 时连续集合与相应二元预算集合对本凸最坏值问题等价；非整数时不能只枚举 0/1 场景。

备用损失上限随风险增加，正常容量随风险下降。设某个池的损失从高风险的 \(L_H\) 降到 \(L_L\)。若原方案启用备用总量超过 \(L_L\)，沿原备用弧将超出的流量改成正常流。由于备用弧是正常弧的子集，转换合法。转换量至多为 \(L_H-L_L\)，由新增正常容量吸收。上游投入、BOM 和交付保持相同，非负启用费下降或保持相同。T2 风险降低也只会放宽产能。因此固定方案的最小缺口对各风险坐标非减。精确枚举仍保留完整顶点集。
