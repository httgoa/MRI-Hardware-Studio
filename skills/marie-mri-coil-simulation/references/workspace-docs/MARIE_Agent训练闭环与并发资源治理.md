# MARIE Agent 训练闭环与并发资源治理

权威上手包位于 onboarding/MARIE_Agent_Quickstart_8Ch_v01/。训练案例使用唯一 CaseTag、独立输入、同名 MSH/JSON、独立 execution 输出和 seed JSON 副本，不读取或覆盖历史 reproduction。

## 执行档

legacy-geometry-only 只允许 light、只读 geometry。training-closed-loop-v1 只对显式配置的隔离案例开放 geometry、stage_a、tmd、stage_c、post。Stage A/TMD/Stage C 需要 exact-run 审批；TMD 还需要活动 JSON canonical lock。

## 资源

prepare 将 worker 数写入冻结 MATLAB 命令；marie_agent_configure_pool 在 load_inputs 前建立精确大小的 Processes pool。每任务最多 64 workers，全局生产上限 96。GPU 0 是独占资源。资源门禁不替代按模型规模估算内存。

## 上游证据

Stage B、Stage C 和 post 的依赖由 agent-case.json 声明。prepare 只选择状态为 succeeded 的最近执行产物，记录路径、生产 RunID、大小和 SHA-256；launch 再检查漂移。runner 通过 MARIE_DEP_<LABEL> 环境变量读取冻结依赖。

## 科学边界

闭环跑通不代表网络或研究验收通过。训练拓扑的历史结果存在互耦门禁失败；不得通过放宽阈值隐藏。post 仅生成 Rx 网络、场、SNR 和噪声基础结果，不把 Rx reciprocity fallback 当作正式 Tx/SAR，也不默认复制 5.6 GB UISNR BASIS。
