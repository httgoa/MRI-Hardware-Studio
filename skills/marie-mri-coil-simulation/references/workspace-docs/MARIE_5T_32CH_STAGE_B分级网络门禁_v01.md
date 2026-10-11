# MARIE 5T 32通道 Stage B分级网络门禁 v01

生效日期：2026-09-08。权威项目文件为
`projects/5t_32ch_loop_dipole_rx/docs/00_governance/STAGE_B_GRADED_NETWORK_GATE_POLICY_v01.md`。

A级保留正式基准门禁：全部前放负载`SP_p<-15 dB`、全部非对角
`SP_s<-12 dB`、谐振偏移`<0.5 MHz`、对称组离散`<3 dB`。

B级仅允许探索性FixedCircuit Stage C：至少28/32通道`SP_p<-15 dB`，其余
全部`<-12 dB`；最差`SP_s<-10.5 dB`，且`SP_s>=-12 dB`的唯一无序通道对
不超过4组并全部属于冻结邻接表。B级必须标为
`exploratory_conditionally_accepted`，不得称为正式或research-validated基准。

B级Stage C之后仍须检查噪声矩阵Hermitian/半正定、最大/平均噪声相关、场完整性、
ROI SNR和g-factor。论文中的50 Ω `S11/S21`不得直接当作MARIE前放负载
`SP_p`或噪声相关。

项目runner结构化输出分别使用`grade_a_pass`、
`eligible_for_exploratory_stage_c`、`coupling_exception_pair_count`和
`coupling_exceptions_all_adjacent`。旧证据不原地改写，使用独立追溯判定文件。

