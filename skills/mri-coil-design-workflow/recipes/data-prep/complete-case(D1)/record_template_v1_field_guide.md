# record_template_v1.json 字段说明

本文档说明 D1（dipole）模块输出记录 `record_template_v1.json` 中每个字段的含义、单位、
何时应被填充，以及结果检查时应关注的要点。参考实例取自已完成的
[record.json](../../../../../results_data_prep/RD_A01/cases/cc_rd_L300_W10_lo40_direct_210/output/record.json)
（case `RD_A01`）。字段来源与生成规则以
[data-prep-complete-case-dipole.md](data-prep-complete-case-dipole.md) 和
[AGENT_BATCH_SIMULATION_PIPELINE.md](../../../../../notes/data_prep/AGENT_BATCH_SIMULATION_PIPELINE.md)
为准；本文件只做字段级速查，冲突时以那两份文件为准。

## 顶层元信息

| 字段 | 含义 | 检查要点 |
| --- | --- | --- |
| `schema_version` | 记录 schema 版本，固定为 `data_prep.case_record.v1` | 不应被修改 |
| `record_id` | 记录唯一 ID，规则 `cc_rd_L<L_line>_W<strip_width>_lo<coil_to_phantom>_direct_210` | 与文件路径、`manifest.csv` 中的 `record_id` 一致 |
| `case_matrix_id` | 对应 `case_matrix_v1.csv` 中的行 ID（如 `RD_A01`） | 用于回查该 case 的设计参数与 `notes` |
| `library_role` | 记录在数据库中的角色，固定 `global_complete`（完整已验证案例） | - |
| `simulation_role` | 对应 `case_matrix_v1.csv` 的 `simulation_role` 列，如 `direct_unmatched_performance` | 需与 case matrix 行一致 |

## `source` — 项目来源

| 字段 | 含义 |
| --- | --- |
| `source_project_path` | 记录的来源标记，本模块固定写 `artifact_generated_from_case_matrix_v1` |
| `project_copy_path` | 本 case 独立 CST 工程副本路径，例如 `projects/data_prep_RD_A01/RD_A01.cst` |
| `build_manifest_path` | 记录几何/参数构建过程的 manifest 文件路径 |
| `model_history_snapshot_path` | 历史树快照路径（该模块通常为 `null`） |
| `schematic_snapshot_path` | 原理图快照路径；direct-port 记录不需要原理图，固定 `null` |

## `geometry` — 几何与拓扑

| 字段 | 含义 | 备注 |
| --- | --- | --- |
| `family` | 几何族，如 `regular_dipole` / `fractionated_dipole` | 对应 case matrix `family` |
| `topology` | 更细的拓扑标签，如 `regular_dipole_direct_port` | - |
| `prototype_fidelity` | 保真度标签，对应 case matrix `prototype_fidelity` | - |
| `model_variant` | 固定 `substrate_free_coil_phantom`，表示无基板模型 | 官方 complete case 必须为此值 |
| `include_substrate` | 是否包含基板/支撑结构，官方 case 固定 `false` | 若为 `true` 说明未遵守无基板策略 |
| `support_stack` | 支撑结构类型，官方 case 固定 `"none"` | - |
| `L_line_mm` | 偶极子总长度 (mm)，对应 case matrix `L_line_mm` | 几何核心参数 |
| `strip_width_mm` | 导体条宽度 (mm)，对应 case matrix `strip_width_mm` | - |
| `coil_to_phantom_mm` | 线圈到体模表面的间距 (mm)，对应 case matrix `coil_to_phantom_mm` | 影响 B1+/SAR 深度 |
| `feed_gap_mm` | 馈电缺口宽度 (mm)，默认 2.0 | - |
| `substrate_pec_thickness_mm` / `board_width_mm` / `board_length_mm` | 基板相关尺寸 | 无基板模型下应为 `null` |
| `segment_count_total` | 分段偶极子（fractionated dipole）分段总数 | 常规偶极子为 `null` |
| `seg_gap_mm` | 分段间隙 (mm) | 常规偶极子为 `null` |
| `segment_lengths_mm` | 各分段长度列表 (mm) | 常规偶极子为空数组 |
| `bridge_count_total` | 分段偶极子桥接元件总数 | 常规偶极子为 `null` |
| `bridge_positions_mm` | 桥接元件位置列表 (mm) | 常规偶极子为空数组 |

## `materials_and_load` — 材料与负载

| 字段 | 含义 |
| --- | --- |
| `phantom_eps_r` | 体模相对介电常数（默认 78.0，模拟人体等效介质） |
| `phantom_sigma_S_per_m` | 体模电导率 (S/m)（默认 0.47） |
| `phantom_rho_kg_per_m3` | 体模密度 (kg/m³)（默认 1000.0，用于 SAR 计算） |
| `phantom_size_mm` | 体模三轴外形尺寸 `[x, y, z]` (mm) |
| `fr4_eps_r` / `fr4_tand` | FR4 基板介电常数/损耗角正切，无基板模型固定 `null` |
| `polycarbonate_eps_r` / `foam_eps_r` | 支撑材料介电常数，无基板模型固定 `null` |

## `electrical_design` — 电气设计参数

| 字段 | 含义 |
| --- | --- |
| `freq_MHz` | 设计/工作频率 (MHz)，本模块固定 210.0（对应 4.7T 质子共振） |
| `port_impedance_ohm` | 端口参考阻抗 (Ω)，默认 50 |
| `field_source_id` | CST 中激励源编号，如 `"[1]"` |
| `network_role` | 网络角色，对应 case matrix `network_role`，如 `direct_port`（无匹配网络，直接馈电） |
| `matching_components.Lt_nH/Lp_nH/Ct_pF/Cp_pF` | 匹配网络串联电感/并联电感/串联电容/并联电容，direct-port 记录固定 `null` |
| `fractionated_bridge.lt_bridge_mode` | 分段偶极子桥接模式（如电感/电容桥） | 常规偶极子为 `null` |
| `fractionated_bridge.bridge_L_nH/bridge_C_pF` | 桥接电感/电容参数 | 常规偶极子为 `null` |
| `fractionated_bridge.bridge_R_ohm` | 桥接电阻 (Ω)，默认 0.0 | - |

## `simulation` — 求解与导出配置

| 字段 | 含义 |
| --- | --- |
| `solver_type` | 求解器类型，本模块为 `"HF Time Domain"` |
| `mesh_type` | 网格类型，本模块为 `"Hexahedral"`（Hex/PBA） |
| `mesh_step_or_accuracy` | 网格/收敛设置，如 `"steady_state_limit_-30dB"` |
| `monitors` | 已启用的场监视器列表，固定 `["h-field", "e-field", "loss"]` |
| `b0_direction` | B0 主磁场方向，固定 `"+z"` |
| `normalization` | 归一化基准，固定 `"1W accepted power"`（所有场量按 1W 入射功率归一） |
| `export_grid_step_mm` | 各场导出的空间步长 (mm)，如 `{hfield:1, efield:1, loss:2, sar10g:2}` |
| `export_subvolume_mm` | 场导出子体积 `[xmin,xmax,ymin,ymax,zmin,zmax]` (mm)，本模块固定体模非零区域 `[-135,135,-160,160,-120.5,-20.5]` |

## `electrical_state` — 实测电气结果（来自求解）

| 字段 | 含义 | 检查要点 |
| --- | --- | --- |
| `p_accepted_W` | 求解得到的实际入射（接受）功率 (W) | 用于所有 B1+/SAR 量的归一化分母，不应为 0 或 `null` |
| `s11_210MHz_dB` | 210 MHz 处的 S11 (dB) | direct-port 未匹配，通常接近 0 dB（严重失配） |
| `s11_min_dB` | 扫频范围内 S11 最小值 (dB) | 用于判断谐振深度 |
| `resonant_frequency_MHz` | 实测谐振频率 (MHz) | 与设计频率 210 MHz 的偏差反映几何/负载效应 |
| `input_R_ohm` / `input_X_ohm` | 端口输入阻抗实部/虚部 (Ω) | 用于阻抗匹配分析 |
| `loaded_Q_est` | 有载 Q 值估计 | 若未计算保持 `null` |

## `field_artifacts` — 导出文件路径

记录各原始场导出文件的相对路径（H 场、E 场、损耗、SAR10g、表面电流的 HDF5，以及
S 参数/功率/阻抗 CSV）。检查要点：

- 路径应真实存在，且指向 `results_data_prep/<case_matrix_id>/cases/<record_id>/` 下的对应文件。
- `sar10g_h5` 必须是 native 导出结果（见 `sar_signature.sar_status`），不能是 loss 代理。

## `b1_signature` — B1+ 场特征（发射场均匀性/穿透）

| 字段 | 含义 |
| --- | --- |
| `unit` | 固定 `"uT/sqrt(W accepted)"`，所有 B1+ 数值已按接受功率归一 |
| `b1p_surface_mean_uT_per_sqrtW` | 体模表面处 B1+ 均值 |
| `b1p_30mm_mean_uT_per_sqrtW` / `b1p_60mm_mean_uT_per_sqrtW` / `b1p_100mm_mean_uT_per_sqrtW` | 体模内 30/60/100 mm 深度处 B1+ 均值 |
| `b1p_at_10cm_mean_uT_per_sqrtW` | 10 cm 深度处 B1+ 均值（与 `b1p_100mm_mean_uT_per_sqrtW` 对应） |
| `b1p_at_10cm_p10/p50/p90_uT_per_sqrtW` | 10 cm 深度处 B1+ 分布的第 10/50/90 百分位数，反映该深度层的均匀性 |
| `b1p_peak_uT_per_sqrtW` | 全场 B1+ 峰值 |
| `b1p_peak_xyz_mm` | 峰值出现的坐标 (mm) |
| `cov_roi` | ROI 内 B1+ 变异系数（标准差/均值），越小越均匀 |
| `half_value_depth_mm` | B1+ 降至峰值一半时对应的深度 (mm)，衡量穿透能力 |
| `penetration_auc_0_150_uTmm_per_sqrtW` | 0-150 mm 深度范围内 B1+ 曲线下面积，综合衡量穿透 |
| `depth_profile_csv` / `lateral_profile_csv` | 深度/横向剖面数据文件路径 |
| `slices_48x48_npz` | 48×48 网格化 B1+ 切片数据（用于可视化/学习） |

## `sar_signature` — 10g 平均 SAR 场特征

| 字段 | 含义 |
| --- | --- |
| `sar_status` | SAR 数据可信等级：`validated_native_h5`（已用 `GetValue` 交叉验证的 native HDF5）> `partial_native_scalar_only`（仅标量，无 HDF5）> `partial`（loss 代理等不完整）> `needs_validation`（未处理） |
| `sar_metric_source` | 计算方法说明，如 `"CST_native_IEEE_C95.3_10g_HDF5_no_rescale_manual_Pacc_normalization"` |
| `unit` | 固定 `"W/kg @ 1W accepted"` |
| `sar10g_max_W_per_kg_per_W` | 10g 平均 SAR 峰值（每 1W 接受功率） |
| `sar10g_p99_W_per_kg_per_W` | SAR 分布第 99 百分位值，比峰值更抗噪声 |
| `sar10g_roi_mean_W_per_kg_per_W` | ROI 内 SAR 均值 |
| `sar_hotspot_xyz_mm` | SAR 热点坐标 (mm) |
| `sar_hotspot_depth_mm` | 热点深度 (mm) |
| `sar_hotspot_distance_to_conductor_mm` | 热点到最近导体表面电流的距离 (mm)，若无表面电流清洗数据保持 `null` |
| `sar_hotspot_concentration` | 热点集中度 = `sar10g_max / sar10g_roi_mean`（近似），越大说明 SAR 分布越集中 |
| `sar_efficiency_10cm` | 10 cm 深度处的 SAR 效率指标 |
| `depth_profile_csv` | SAR 深度剖面文件路径 |
| `slices_48x48_npz` | 48×48 网格化 SAR 切片数据 |

**验证要点**：`sar10g_h5` 必须满足 HDF5 中 `SAR.max()` 与同次 no-rescale
`SAR.GetValue("max sar")` 相对误差 <5%（参见 `qa.notes` 记录的相对误差）。

## `current_signature` — 表面电流特征

| 字段 | 含义 |
| --- | --- |
| `current_status` | 计算状态，如 `"computed_from_surface_current_h5"` |
| `current_peak_A_per_sqrtW` | 表面电流峰值 (A，每 1W 接受功率) |
| `current_mean_A_per_sqrtW` | 表面电流均值 |
| `current_center_to_end_ratio` | 中心电流与末端电流之比，衡量电流分布形态（偶极子中心通常电流最大） |
| `current_left_right_symmetry_error` | 左右对称性误差，越接近 0 说明几何/网格越对称 |
| `current_phase_span_deg` | 电流相位跨度 (度) |
| `current_hotspot_region` | 电流热点所在区域标签，如 `"edge"` / `"center"` |

## `learning_card` — 面向学习/检索的摘要

| 字段 | 含义 |
| --- | --- |
| `design_tokens` | 设计标签数组，如 `["coil_and_phantom_only", "regular_dipole", "direct_port"]`，用于检索/分类 |
| `field_summary_text` | 场特征的自然语言摘要，未生成时为 `null` |
| `dominant_effect_labels` | 主导效应标签（如"近场增强""失配损耗"等），未生成时为空数组 |
| `prompt_card_jsonl_path` | 对应的 prompt 卡片 JSONL 文件路径 |

## `lineage` — 记录谱系

| 字段 | 含义 |
| --- | --- |
| `parent_record_id` | 父记录 ID（若本记录由参数扰动/衍生而来） |
| `action_type` | 衍生动作类型，如参数扫描、匹配网络添加等 |
| `changed_params_json` | 相对父记录变化的参数（JSON 字符串） |
| `direction_label` | 变化方向标签（如"增大耦合""提高匹配"） |

顶层 case（`source_seed=template`）的这些字段通常为 `null`。

## `qa` — 质量检查状态

| 字段 | 含义 | 检查要点 |
| --- | --- | --- |
| `qa_status` | 总体状态：`needs_validation`（初始）→ `validated`（通过校验） | 未验证前不应视为最终结果 |
| `qa_flags` | 已完成检查项标签数组，如 `native_sar10g_h5_validated_against_getvalue`、`surface_current_metrics_generated` 等，逐项对应 [data-prep-complete-case-dipole.md](data-prep-complete-case-dipole.md) 的 QA Flags 清单 | 缺失关键 flag 说明该环节未完成 |
| `schema_pass` | 是否通过 schema 校验（字段完整/类型正确） | `false` 说明记录结构有问题 |
| `field_archive_status` | 场文件归档状态，如 `"complete"` | 若非 complete，需检查 `field_artifacts` 中文件是否缺失 |
| `notes` | 自由文本备注，通常记录 SAR HDF5 与 `GetValue` 的相对误差等关键校验数据 | 用于快速判断 SAR 数据可信度 |

## 快速核对清单

检查一条记录是否"完整可信"时，建议按以下顺序核对：

1. `qa.qa_status == "validated"` 且 `qa.schema_pass == true`。
2. `electrical_state.p_accepted_W` 非 `null` 且非 0（所有归一化的基础）。
3. `sar_signature.sar_status == "validated_native_h5"`，且 `qa.notes` 中记录的相对误差 <5%。
4. `field_artifacts` 中列出的文件路径均存在于磁盘。
5. `geometry.include_substrate == false` 且 `geometry.model_variant == "substrate_free_coil_phantom"`（确认符合本模块无基板策略）。
6. `b1_signature` / `sar_signature` / `current_signature` 中的关键统计量（peak/mean/roi）均为数值而非 `null`。
