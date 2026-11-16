# V3.3 有效界 C&CG

以冻结的准备网络及场景追索为约束。算法仅调整每轮分离的查询范围、次序和判据。四组共用 Master、预算、参数、单场景添加及独立全场景重放。

令受限 Master 解为 `(x,q,a,c)`，共同准备经济成本为 `K(x)`。对场景 s，验证一套追索同时满足 `OT >= q`、`A <= a`、`H <= c-K(x)`。一套经重放的整数解即提供三个界。其 OT 是单场景最大 OT 的下界，其 A 是共同 OT 下限下最小积压的上界，其 H 是共同服务与积压阈值下最小持有成本的上界。三个界来自同一见证。不同方案的独立标量界不能拼接。

对于已建入 Master 的场景，当前 Master 已有该见证。缓存只在完全相同的期初库存、库存上下界、共享库容涉及的位置和总容量、场景 ID 以及同一冻结实例下复用。在更换目标阈值后重新检查缓存见证的三个值。一个旧方案在库存或库容已变时没有证书用途。历史违反次数只决定查询顺序，不能排除任何无覆盖或无见证的场景。

求解无目标的阈值可行性 MILP。任何经过原约束重放的可行解就能关闭该场景的当前检查。经求解器认证不可行则当前三元目标无法在该场景同时实现，加入它的一整个追索块。未决状态没有有效见证时标记 BLOCKED。

```text
active = {NOM}
repeat:
    solve the exact three-stage restricted master
    set thresholds = (q, a, c - K(x))
    if dominance enabled: query the proven dominating representatives
    else: query all legal scenarios
    if bound variant enabled:
        inspect historical violations first
        reuse active or compatible cached witnesses where possible
        solve remaining joint-threshold feasibility problems serially
        choose the first scenario with proven infeasibility
    else:
        use Plain exact lexicographic separation on the query set
    if a scenario violates: append its block and continue
    independently replay all original scenarios and all three objectives
    certify only when replay agrees
```

以 `(-q,a,c)` 表示最小化词典序目标。删去追索块会扩大可行域，所以 Master 的最优三元组是全模型的词典序下界。当上述阈值被全部场景同时满足时，Master 的第一阶段方案可提升到全场景可行解并实现同一界。使用支配覆盖时，覆盖者的同一追索选择可复制给覆盖对象。在发现违反时加入的场景此前不在 Master，因此每轮严格增加一个块，有限集合下最终结束或求解器明确停止。

该方法允许最坏场景的发现顺序与 Plain 不同。概率、预测和学习分数均未进入证书。最终全场景重放用独立追索 MILP，并沿用 PR #9 的证书门槛。
