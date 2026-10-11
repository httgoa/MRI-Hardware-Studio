# MARIE 5 T 16通道联合 TMD 解决方案

## 1. 目标

在不重跑三维电磁 Stage A 的条件下，复用现有 `YPn`，联合满足：

```text
所有前放加载反射 SP_p < -15 dB
所有常规多端口非对角 SP_s < -12 dB
最大谐振偏移 < 0.5 MHz
SP_s 互易性相对误差 < 1e-6
```

历史结果证明同一几何下 `S10,9` 可在 `-15.005` 到 `-9.732 dB` 之间变化，因此先解决电路目标权衡，不立即修改几何。

## 2. 联合目标

最终粒子代价为：

```text
matchRatio    = max_p(|SP_p(p)|)       / 10^(-15/20)
couplingRatio = max_i!=j(|SP_s(i,j)|) / 10^(-12/20)
cf            = max(matchRatio, couplingRatio)
```

`SP_p` 和 `SP_s` 均使用与最终校准一致的有限 Q 元件模型。只有 `cf<1` 时，匹配与互耦同时通过；二者不能互相补偿。

## 3. 需要同步到 Linux 的文件

```text
RUN_5T_16CH_TMD_ONLY.m
src/src_physics/src_electronics/co_simulation/
  co_sim_cost_functions/
    matching_and_tuning_and_preamplifierdecoupling_loss_aware.m
  co_sim_runners/
    runner_M_T_PD_loss_aware.m
  co_sim_master_files/
    co_simulation_Rx_optim_loss_aware.m
```

同步后执行：

```matlab
cd('/home/<user>/marie-tools');
startup;
clear functions;
rehash path;

which co_simulation_Rx_optim_loss_aware -all
which runner_M_T_PD_loss_aware -all
which matching_and_tuning_and_preamplifierdecoupling_loss_aware -all
```

三个路径必须指向 `/home/<user>/marie-tools/src/...` 下的新版本。

## 4. 保护当前结果并准备种子

当前 `063923` 电路匹配合格但互耦失败，必须先保留：

```matlab
coilJson = fullfile(pwd,'data','coils','wire_files','Custom', ...
    'Sphere16Rx_2Row_R115_H90_Span50_Z25_Stagger22p5.json');

matchOnlyBackup = [coilJson '.accepted_match_only_20260807_063923'];
if exist(matchOnlyBackup,'file')~=2
    copyfile(coilJson,matchOnlyBackup);
end
```

推荐从早期互耦较好的电路快照开始：

```matlab
seedJson = [coilJson '.before_TMD_20260807_053238'];
assert(exist(seedJson,'file')==2,'Historical seed JSON is missing');
copyfile(seedJson,coilJson);
```

不要使用 `.before_TMD_045248` 代替 `045248` 的输出；`before` 文件保存的是该轮运行前状态。`before_TMD_053238` 更可能对应 `045248` 结束后的活动电路。恢复后必须检查元件范围和 symmetry，不能只根据文件名假定内容正确。

## 5. 验证种子配置

```matlab
J = jsondecode(fileread(coilJson));
E = J.coil_configuration.elements;

assert(numel(E)==128);
assert(sum(strcmp({E.type},'port'))==16);

fprintf('Ch | Cp1 range pF | Ls range nH | Cp2 range pF | Cseg range pF\n');
for ch = 1:16
    idx = (ch-1)*8+(1:8);
    fprintf('%2d | %5.1f..%5.1f | %5.1f..%5.1f | %5.1f..%5.1f | %5.1f..%5.1f\n', ...
        ch,E(idx(1)).optim.minim(1)*1e12,E(idx(1)).optim.maxim(1)*1e12, ...
        E(idx(1)).optim.minim(2)*1e9,E(idx(1)).optim.maxim(2)*1e9, ...
        E(idx(1)).optim.minim(3)*1e12,E(idx(1)).optim.maxim(3)*1e12, ...
        E(idx(2)).optim.minim*1e12,E(idx(2)).optim.maxim*1e12);
end
```

批准范围应为：

| 元件 | 下界 | 上界 |
|---|---:|---:|
| Cp1 | 1 pF | 20 pF |
| Ls | 20 nH | 100 nH |
| Cp2 | 40 pF | 140 pF |
| Cseg | 3 pF | 8 pF |

然后重新执行操作指南中的 symmetry 内部 ID 无碰撞检查。

## 6. Runner 设置

确认 `RUN_5T_16CH_TMD_ONLY.m` 顶部为：

```matlab
useLossAwareTMD = true;
targetReturnDB = -15;
useCouplingConstraint = true;
targetCouplingDB = -12;
useFullHardBounds = true;
```

`useFullHardBounds=true` 会让最终联合阶段搜索完整 JSON 范围，避免被当前坏互耦电路附近的 `0.5-1.5` 倍局部窗口限制。计算量会高于只匹配版本。

## 7. 运行

```matlab
RUN_5T_16CH_TMD_ONLY;
```

运行开始时应显示：

```text
Running joint loss/coupling-aware Rx TMD using precomputed YPn
```

如果仍显示旧的 `Running loss-aware standalone...`，说明服务器 runner 或函数路径未更新。

## 8. 验收

最终必须显示：

```text
Match / resonance / coupling / reciprocity pass: 1 / 1 / 1 / 1
```

并执行：

```matlab
assert(metrics.match_pass);
assert(metrics.resonance_pass);
assert(metrics.coupling_pass);
assert(metrics.reciprocity_pass);
assert(metrics.worst_loaded_margin_dB > 0);
```

同时检查：

- 最差互耦不应只比 `-12 dB` 好几个百分之一 dB；建议至少保留 0.5–1 dB 数值裕量。
- 最大频偏不应长期贴近 0.5 MHz 门槛。
- 最强耦合端口对应与三维几何相邻关系一致。
- 四类通道的元件值没有压在批准边界。

## 9. 失败后的决策

| 结果 | 下一步 |
|---|---|
| 匹配通过、互耦失败，且不同联合轮次互耦明显变化 | 调整联合目标裕量或搜索策略，继续复用 `YPn` |
| 互耦通过、匹配失败 | 检查失败通道族及其元件边界，不立即改几何 |
| 两项轮流通过但始终不能同时通过 | 记录 Pareto 冲突，进入 Span/重叠几何扫描 |
| 多个联合轮次最差端口对和数值稳定不合格 | 判定几何主导，建立新 case 并重跑 Stage A |
| 四项全部通过 | 冻结 JSON，进入 Stage C |

禁止在失败后直接删除 `YPn`。只有修改 Loop 几何、体模、频率、网格或端口物理映射时才需要重跑 Stage A。
