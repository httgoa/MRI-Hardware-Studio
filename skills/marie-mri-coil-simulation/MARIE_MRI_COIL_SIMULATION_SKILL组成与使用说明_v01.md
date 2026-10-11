# MARIE MRI Coil Simulation Skill：组成与使用说明

日期：2026-09-24  
盘点对象：`/home/<user>/marie-tools/marie-mri-coil-simulation skills/`  
性质：skill 源码包组成说明；不修改 MARIE 算法、仿真输入或运行结果

## 1. 总体结论

`marie-mri-coil-simulation` 不是单一提示词文件，而是一个可安装、可离线查询、带安全运行工具和复现实例的 MARIE 3.0 专用 skill 包。它由以下五层组成：

```text
SKILL.md：任务触发、总原则和工作流
    ↓
references/：规则、专题知识、工作区文档快照和架构登记
    ↓
assets/：MATLAB 示例脚本与受控 Agent 执行工具备份
    ↓
scripts/：文档检索、会话初始化、manifest 和架构维护
    ↓
agents/openai.yaml：OpenAI/Codex 展示名称和默认调用提示
```

文件数量、逻辑字节数和哈希由 `references/bundle-manifest.json` 与发布前验证脚本动态计算；本说明不再固化容易过期的总数。

| 分区 | 文件数 | 主要职责 |
|---|---:|---|
| 根目录 | 2 | `SKILL.md` 主入口与本组成说明 |
| `agents/` | 1 | OpenAI/Codex 界面元数据 |
| `references/` | 动态 | 专题参考、工作区文档快照、manifest、上游许可和架构登记 |
| `assets/` | 动态 | MATLAB 参考脚本与 Agent 工具/测试文件 |
| `scripts/` | 4 | 维护、检索和会话初始化脚本；不包含运行缓存 |
| `tests/` | 动态 | UISNR 数值不变量与回归测试 |

发布包不包含 `.pyc` 或 `__pycache__`。本说明是描述性文档，不属于运行组件。

## 2. 目录结构

```text
marie-mri-coil-simulation/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── architecture-interfaces.md
│   ├── bundle-manifest.json
│   ├── document-index.md
│   ├── rx-array-validation.md
│   ├── snr-measurement-normalization.md
│   ├── storage-layout.md
│   └── workspace-docs/                 # 28 份工作区文档快照
├── assets/
│   ├── matlab-scripts/                 # 9 个 MATLAB 参考脚本
│   └── marie-agent-phase1/             # 受控执行工具与自测
├── scripts/
│   ├── query_marie_docs.py
│   ├── session_init.sh
│   ├── record_architecture_update.py
│   ├── refresh_bundle_manifest.py
└── MARIE_MRI_COIL_SIMULATION_SKILL组成与使用说明_v01.md
```

## 3. 主入口：`SKILL.md`

[`SKILL.md`](SKILL.md) 是 skill 的行为入口，主要包含：

1. **触发范围**：MARIE 模型创建、运行、验证、排障、后处理、UISNR、SNR、TMD、Tx/Rx、数据管理及架构维护；
2. **案例隔离原则**：使用唯一 CaseTag/RunTag，不覆盖已验证参考资产；
3. **存储治理**：系统 SSD 保存控制面，数据盘保存大型 MAT/BASIS/checkpoint；
4. **新会话初始化**：读取规则、运行只读 bootstrap、检查最新证据；
5. **Stage A/B/C 工作流**：原始网络、TMD、电路冻结与最终场计算必须分阶段；
6. **设计规则**：MSH/JSON 对应、端口顺序、几何变更后的缓存失效等；
7. **结果门禁**：区分数值完成、网络通过、场/噪声验证和 research-validated；
8. **UISNR 边界**：区分 `geo_flag=2` 表面支撑约束最优 SNR 与更接近绝对 UISNR 的 `geo_flag=3` 壳层近似；
9. **TMD 硬边界**：优化器不得静默越过电容/电感声明范围；
10. **失败处理**：保留原始错误栈，不以放宽阈值或替换系统库掩盖问题。

它给出的是决策边界和工作流，而不是完整 MARIE 教科书。具体问题由 `references/document-index.md` 路由到专题文档。

## 4. Agent 元数据：`agents/`

[`agents/openai.yaml`](agents/openai.yaml) 定义 OpenAI/Codex 侧的展示信息：

- 展示名：`MARIE MRI Coil Simulation`；
- 简短说明：构建、验证和查询 MARIE MRI 仿真；
- 默认提示：调用 `$marie-mri-coil-simulation` 查询内置指南或建立可复现仿真。

该文件不包含仿真算法，也不授权高成本计算；权限仍由系统、用户和项目 `AGENTS.md` 决定。

## 5. 知识层：`references/`

### 5.1 直接专题参考

| 文件 | 作用 |
|---|---|
| [`document-index.md`](references/document-index.md) | 把常见问题路由到相应文档和检索关键词 |
| [`architecture-interfaces.md`](references/architecture-interfaces.md) | 追加式记录架构、公共接口、兼容性和证据；最新登记截至 2026-09-14 |
| [`bundle-manifest.json`](references/bundle-manifest.json) | 记录快照日期、来源、文件大小与 SHA-256 |
| [`rx-array-validation.md`](references/rx-array-validation.md) | Rx 阵列网络、场、噪声和 SNR 验收提示 |
| [`snr-measurement-normalization.md`](references/snr-measurement-normalization.md) | 从 MARIE 原始 SNR 到采集协议/实测 SNR 的归一化边界 |
| [`storage-layout.md`](references/storage-layout.md) | SSD/HDD 分层、容量门禁、迁移和保留等级 |

### 5.2 `workspace-docs/`：离线工作区快照

该目录含 28 份 Markdown，总计 508,635 B。它们是从 MARIE 工作区抽取的自包含快照，在原工作区不可用时提供离线知识；有活动工作区时，当前源码和运行证据优先于快照。

文档按用途可分为：

- **规则与重入**：`AGENTS.md`、`MARIE_Agent_Harness.md`、`START_HERE.md`、`MARIE_新会话初始化机制.md`；
- **远程执行与训练闭环**：`MARIE_Codex远程开发具体实施指南.md`、`MARIE_Agent训练闭环与并发资源治理.md`、`MARIE_Phase2B_fake_selftest_20260811.md`；
- **输入、源码和数据结构**：JSON 配置、数据目录、源码模块、tools 架构；
- **Runner 与电路**：Runner 指南、TMD 教程、16 通道联合 TMD、5 T 32 通道分级 Stage-B 门禁；
- **建模与可视化**：模型设计组合、可视化脚本、中文帮助；
- **UISNR**：实现与代码分析、独立复现方案和风险；
- **案例历史**：5 T 8/16 通道操作指南、16 通道日志和清理模板；
- **优化架构**：WP7 优化框架和 3 T Duke/Hugo 项目重入文件；
- **上游说明**：快照内 `README.md`。

`document-index.md` 要求先搜标题和关键词，再完整阅读命中章节，并把历史日志视为案例证据而非通用规则。

## 6. 参考资产：`assets/`

### 6.1 `assets/matlab-scripts/`

这里保存 9 个路径相对独立的 MATLAB 参考备份：

| 文件 | 角色 |
|---|---|
| `CREATE_5T_16CH_DOUBLE_ROW_CASE.m` | 创建 5 T、16 通道双排 Loop 示例几何与输入 |
| `RUN_5T_16CH_SPHERE.m` | 完整 MARIE 求解示例 |
| `PRECOMPUTE_5T_16CH_EM_NETWORK.m` | Stage A：生成原始 `YPn` 和可选 checkpoint |
| `RUN_5T_16CH_TMD_ONLY.m` | Stage B：基于已有 `YPn` 执行调谐/匹配/去耦 |
| `FINALIZE_5T_16CH_FROM_CHECKPOINT.m` | Stage C：冻结电路后计算最终场和 SNR |
| `POST_5T_16CH_SPHERE.m` | 16 通道网络、B1−、SNR/UISNR 与 Tx 条件后处理 |
| `POST_5T_8CH_SPHERE.m` | 8 通道球形体模后处理 |
| `installer.m` | MEX/工具箱安装和编译参考 |
| `startup.m` | 最小 MATLAB 路径初始化示例 |

这些是**参考备份**，不是活动项目的唯一 runner。正常使用时应复制到新版本案例再修改，不能直接覆盖已验证资产；其中部分脚本带历史路径和案例名，不能无检查直接运行。

### 6.2 `assets/marie-agent-phase1/`

该目录含 15 个文件，提供受控的远程执行证据链：

```text
inspect → prepare → approve（如需要）→ launch
                              ↓
                    production_worker/runtime
                              ↓
                        status / tail
```

主要组件：

| 组件 | 作用 |
|---|---|
| `inspect.sh` | 调用工作区只读 `session_bootstrap.sh` |
| `prepare.py/.sh` | 冻结 runner、依赖、哈希、命令和资源，不启动 MATLAB |
| `approve.py/.sh` | 将一次明确授权绑定到单个已准备 RunID，带有效期与单次消费 |
| `launch.py/.sh` | 校验快照、依赖、审批与命令后提交 detached tmux |
| `production_worker.py` | 执行 allowlist、worker 总量、GPU/JSON/案例锁等生产门禁 |
| `runtime.py` | 原子状态写入、锁、审批消费和状态迁移原语 |
| `status.sh` | 查看科学状态与 execution 状态 |
| `tail.sh` | 查看 execution JSON 和最新日志 |
| `matlab/marie_agent_configure_pool.m` | 在 MATLAB 内配置并核验并行池 |
| `tests/fake_worker.py`、`tests/selftest.py` | 不调用 MATLAB 的状态机、锁、审批和 tmux 自测 |

该资产是参考备份；活动工作区存在 `tools/marie-agent/` 时，以活动实现为准。

## 7. 辅助脚本：`scripts/`

| 文件 | 作用 | 是否写入 |
|---|---|---|
| `query_marie_docs.py` | 对 28 份文档快照做普通/正则/标题搜索，可输出 JSON | 只读 |
| `session_init.sh` | 便携式调用活动工作区 `tools/session_bootstrap.sh` | 只读 |
| `record_architecture_update.py` | 向 `architecture-interfaces.md` 追加结构化架构变更 | 写入；仅架构更新时使用 |
| `refresh_bundle_manifest.py` | 重建快照日期、大小和 SHA-256 manifest | 写入；更新 bundle 后使用 |

常用查询示例：

```bash
python "marie-mri-coil-simulation skills/scripts/query_marie_docs.py" --files
python "marie-mri-coil-simulation skills/scripts/query_marie_docs.py" "UISNR"
python "marie-mri-coil-simulation skills/scripts/query_marie_docs.py" "Stage A" --headings
```

## 8. 组件如何协同

```text
用户提出 MARIE 任务
        ↓
SKILL.md 判断任务类型、权限、风险和证据要求
        ↓
document-index + query_marie_docs 定位专题知识
        ↓
有活动工作区？ ──是──> 核对当前源码、AGENTS、输入和运行证据
        │
        否
        ↓
使用 workspace-docs 与 matlab-scripts 作为离线参考
        ↓
静态检查 → 几何门禁 → Stage A → Stage B → 固定电路 Stage C
        ↓
rx-array-validation / SNR normalization / UISNR 边界验收
        ↓
保存 CaseTag、RunTag、manifest、日志、指标和未验证项
```

核心设计思想是：skill 提供规则和检索层，活动 MARIE 工作区提供当前事实，运行证据提供最终可审计结论。三者不能互相替代。

## 9. 完整性与安装状态

### 9.1 Manifest

`bundle-manifest.json` 使用 schema 2，记录快照日期、经过去标识化的来源位置、受管文件大小和 SHA-256。发布前运行 `python scripts/refresh_bundle_manifest.py --skill-root <skill-root>`，然后逐项验证文件存在、大小与哈希一致。

Manifest 明确排除自身和 `refresh_bundle_manifest.py`，避免自引用；本组成说明同样属于包说明而非运行组件。`snr-measurement-normalization.md`、UISNR 专题、测试和上游许可说明均由当前生成器纳入受管文件。

### 9.2 源码包与安装包

仓库中的发布目录名必须与 front matter 一致：`skills/marie-mri-coil-simulation/`。安装到本地时复制到所选 Codex skills 根目录下的同名子目录。不得依赖某个用户的 home、MATLAB 安装位置或内部服务器；使用 `MARIE_ROOT`、`MATLAB_BIN` 和外部配置提供环境路径。

### 9.3 自测

`assets/marie-agent-phase1/tests/selftest.py` 在允许临时 tmux 的环境中通过以下 11 项检查：

```text
exit0, exit42, signal, forbidden_executable, case_lock,
canonical_json_alias_lock, tmux_detached, event_revision,
approval_single_use, startup_unknown, orphan_recovery
```

自测结果明确为 `matlab_invoked=false`，没有启动 MATLAB 或正式仿真。首次在受限沙箱内运行时因无权连接 tmux 被阻止，切换到允许 tmux 的执行环境后通过。

## 10. 使用边界与注意事项

1. `workspace-docs/` 是 2026-09-14 快照，不自动代表 2026-09-24 活动工作区状态；
2. 当前源码、输入、CaseTag/RunTag 和实际运行日志的证据级别高于 bundle 快照；
3. MATLAB 资产是示例或备份，不能直接覆盖现役 runner、JSON 或验证结果；
4. `approve/launch` 工具不替代用户授权，高成本任务仍需精确 CaseTag、命令、资源和输出路径审批；
5. `Simulation completed successfully` 只证明数值流程结束，不等于网络、场、噪声或研究结论通过；
6. 上游与许可来源见 `references/upstream-and-license.md`；
7. 不应把运行缓存、历史案例日志或旧工作区快照误当成现役算法真身。

## 11. 一句话定位

该 skill 是 MARIE 3.0 MRI 线圈仿真的“规则入口 + 离线知识库 + 示例资产 + 受控执行证据工具箱”：它帮助 Agent 正确规划、查证、运行和验收仿真，但科学结论仍必须来自当前工作区和具体 CaseTag/RunTag 的实际证据。
