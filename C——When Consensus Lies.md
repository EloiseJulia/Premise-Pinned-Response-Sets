C——When Consensus Lies论文解读


## 标题

When Consensus Lies: Fake Redundancy in Multi-Model AI Systems

## 作者

匿名投稿（ANONYMOUS AUTHOR(S)，双盲审稿状态）

## 发表会议/期刊

Proc. ACM Hum.-Comput. Interact., Vol. 8, No. CSCW2（2026年11月，Article XXX，29页）

## 研究领域

HCI / CSCW 方向的人–AI 协作与信任研究，交叉 LLM 多智能体集成与不确定性检测：研究"同一 prompt 广播给多个模型"这类界面中的共识可信度问题。

---

# 一句话总结

当决定性的消歧条件被丢在 prompt 之外时，跨厂商、跨能力层的多个 LLM
会**静默地收敛到同一个错误解读**（CD≈0.53，n_eff=1.10），论文用可执行金标准基准量化了这种"伪冗余"，并给出一个黑盒检测器（AUROC 0.895）在推理时标出该风险。

---

# 研究问题（Research Question）

核心问题（用我的话重述）：**多模型"都同意"这一显示，在什么条件下是有效证据，在什么条件下只是同一个盲点被重复了 k 次？**

论文把这个界面层问题化约为一个可控变量：**决定答案的那句话在不在 prompt 里**。

- **RQ1（regime／机制）**：wrong-consensus（收敛性错误）是否由"消歧信息的位置"（prompt 外 vs prompt 内）决定，而非由任务难度或模型能力决定？- H1_external：消歧线索在 prompt 外 → 高收敛错误
- H2_derivable：消歧线索在 prompt 内 → 收敛错误≈0
- **RQ2（冗余性）**：多加 agent 是否增加**独立证据**？聚合相对单 agent 有增益吗？有效集成规模 n_eff 是多少？
-
**RQ3（能力/厂商）**：这个失效是"弱模型问题"或"单一厂商问题"吗？推理层模型和跨厂商混合池能否恢复独立性？
- **RQ4（剂量）**：删除的消歧子句数 k 增加，收敛错误是否单调上升？
- **（Study 2 隐含 RQ5）**：能否在**无 ground
truth、黑盒、跨厂商**条件下，于推理时检测出"模型在自信地猜一个未言明前提"这一状态？现有 SOTA（semantic entropy）为什么在这里失效？

---

# 为什么这个问题重要

- 多模型同 prompt 界面（ChatHub、Open WebUI、Poe multi-bot、Google AI Studio Compare、PromptQuorum、MultipleChat）已经把"N/N models agree"当成**认知卖点**（"提升信心""减少幻觉"），但审计显示 9 个平台**无一**提供输入侧充分性信号。
- 聚合的认识论保证（Condorcet、群体智慧、ensemble 误差分解）**前提是误差近似独立**；同 prompt 广播恰好破坏该前提，却继承了它的说辞。
- 人类存在稳健的 **correlation neglect**：决策者用"一致程度"代理信心，几乎不折扣来源之间的相关性，因此这种界面正好击中人的系统性偏差。
- 失效是**静默的**（abstention≈0.03%），没有任何内部信号提醒用户，错误会直接流入下游 pipeline（预算分桶、日程计算等）。
- 现有不确定性检测（semantic entropy）在这一象限**结构性失明**：错误是"自信且稳定"的，重采样看不到。

---

# 核心假设（Key Assumptions）

- **假设1（信息边界假设）**：agent 的解读过程只由"保留下来的 prompt"决定；被上游 handoff 丢弃的子句不会以其他方式进入模型（如通过任务措辞的间接线索或预训练记忆）。- 合理性：中等偏高。构造上成立，但"外部约定"本身可能在预训练里有分布性痕迹，模型只是选了先验高的那支——论文其实正是在利用这一点（reversed benchmark），因此该假设与其说是前提不如说是操纵手段。
- **假设2（可执行金标准=正确性）**：正确性由 `check()`
运行代码判定即等价于任务正确性。
- 合理性：对 code_spec 较强；对 policy_qa 较弱——只匹配最终 `{"amount": float}` 数值，不检查推理路径，存在"对的数字、错的理由"。作者自己承认这是有限行为检查。
- **假设3（交换性 exchangeability）**：同一 cell 内不同家族、不同能力层的 agent 误差共享一个共同的 pairwise 相关系数，因此 ICC / n_eff 公式适用。
- 合理性：偏弱，是理想化。作者已披露并用 model-free 的 pairwise agreement 与 Fleiss' κ 做交叉印证，处理算是诚实。
- **假设4（构造的 trap 代表真实世界的上游信息丢失）**：人为删除子句 ≈ 现实中跨人–工具–agent handoff 的上下文丢失。
- 合理性：生态效度未验证。作者主动放弃 prevalence 主张，只主张 failure **mode**。
- **假设5（default-check
筛选不改变机制）**：入选条件是"无知的强模型会产出预定
foil"，这一筛选只影响率不影响机制。
- 合理性：有直接反证据支撑（24 个未筛选 k=1 item，CD=0.685 [0.521,0.839]，不衰减），但注意未筛选样本量很小。
- **假设6（LLM 自曝前提是"自己的"）**：detector 的 self-surface prompt 从不提及 gold key，因此不泄漏答案轴。
- 合理性：由跨家族模型做 anti-leakage 审计，但仍是 prompt 级防泄漏，不能完全排除任务措辞本身提示了轴。
- **假设7（simulated-user oracle
可代表真实澄清收益）**：给出被删约定后，用户能补上它。
- 合理性：**明显偏乐观**，且与论文自身叙事冲突——该子句是在上游 handoff 丢的，键盘前的用户很可能也不掌握。作者明确标注为上界。

---

# 核心创新点（Key Contributions）

##
创新点1：把"多模型共识"重构为**证据独立性**问题，并给出可开关的因果轴

### 做了什么

提出 **fake redundancy**（伪冗余）与 **convergent
delusion**（收敛性妄断，CD）两个构念：在共享信息边界下，名义上多样的 agent 形成"解读单一栽培（interpretive
monoculture）"。用**单一操纵变量**——决定性消歧子句在 prompt 内还是外——把失效开/关：H1 CD≈0.53、H2 CD=0.00；同一基任务内 k=0 vs k≥1 的 ΔCD=0.82 [0.73,0.90]。

### 和已有工作相比新在哪里

- Kim et al. [22] 只是**观测**到跨厂商误差相关；Estornell & Liu [14] 是**理论**证明 debate 会收敛到共同误解；Yang et al. [50] 说明欠规范**降低准确率**；algorithmic monoculture [23] 讲**系统层**相关后果。
- 本文把这些拆开的片段合成一个**受控、预注册、能力无关、可执行金标准**的因果轴，并把落点放在**界面层问题**（何时显示的共识值得信任），度量的是 CD 而非一般误差相关或准确率。

### 是否是真正创新

**中等偏强创新（概念层强、现象层中等）。** 现象本身对熟悉 ensemble 理论的人不算意外（ρ→1 ⇒ n_eff→1
是教科书结论），真正新的是：(a)
把"位置"而非"能力"识别为可操作的开关变量；(b)
用可执行金标准让"一致"与"正确"在定义上分离；(c) 把它接到 CSCW 的界面设计问题上。扣分项：items 是人为构造且经默认行为筛选。

## 创新点2：LPP 检测器 —— 从"采样波动轴"换到"前提敏感度轴"

### 做了什么

黑盒、仅推理（无 logits/梯度）的三步检测器：(1) 通用 prompt
让模型**自曝**决策关键的未言明前提；(2)
把每个前提**反事实钉住**到模型自己给的候选值，各跑一遍；(3) 用**可执行等价性**（`_runner_compare`，FLOAT_TOL=1e-9，union-find）聚类答案，取簇熵 H_ctx-self。当 H_ctx-self > τ=0 且 H_seed ≤ τ_s=0.5 bits 时告警。结果：pooled AUROC **0.895** [0.815,0.966]，semantic entropy 仅
**0.581**（ΔAUROC=0.314，预承诺阈值≥0.15），6 个模型/3 家族/2 层一致。

### 和已有工作相比新在哪里

- 与 semantic entropy [15] 正交：后者听"犹豫"，本文的危险信号恰恰是"稳定"。
- 与 ICE（Input Clarification Ensembling）[20] 的区别在 **target / mechanism / setting**：瞄准 danger quadrant、用可执行等价聚类而非数据集金标、黑盒可跨厂商部署。

### 是否是真正创新

**中等创新。** 关键削弱来自作者自己的诚实
ablation：**只做"要求模型列出假设"（requirements-probing）就已达 0.810**，反事实 pinning 只多加 +0.085
[0.01,0.19]。也就是说，大部分信号来自"问一句你假设了什么"，而 pinning 这个真正精巧的部分是增量优化。定位应为"揭示了一个正交轴 + 一个工程化实现"。

## 创新点3：可执行金标准协议 + 依赖度量学

### 做了什么

54 个任务变体（40 H1_external / 14 H2_derivable，k∈{0,1,2,3}），三域（code_spec / data_analysis / policy_qa）；答案的**解读标签**由确定性 checker 判定，无任何 LLM judge；对抗性 foil 校验器 fail-closed（一个候选匹配多个 checker 就抛 `AmbiguousLabelError`）；130/130 item 认证互相可区分，163 个测试通过。依赖性用 pairwise wrong-agreement=0.98、Fleiss' κ=0.97、ICC=0.89、n_eff=1.10、以及独立性反事实 Δ=+0.245 [0.234,0.257] 联合刻画。

### 是否是真正创新

**工程优化 + 方法学贡献。** 单看没有理论新意，但它是让 RQ1 结论可信的关键基础设施——"models agree"与"models are
right"在定义上被分开，这一点很多同类工作做不到。

## 创新点4：landscape audit（6/9 平台表格化）

**弱创新 / 已有材料重组。**
快照式的公开文档编码，无使用量、无真实危害数据，作用是动机而非证据。

---

# 方法拆解（Method）

## Study 1：两 regime 对照实验

### 输入

- 54 个冻结、预注册的任务变体（3 域）；每项固定目标解读 I₀ + 枚举 foil I₁…；ambiguity level k∈{0,1,2,3}。
- 模型 roster：- Homogeneous single: OpenAI `gpt-5.4`
- Heterogeneous pool: `gpt-5.4` / `claude-sonnet-4.6` / `gemini-3.1-pro-preview`
- Reasoning tier: `gpt-5.6-sol` / `claude-opus-4.8` / `gemini-3.1-pro-preview`
- Weak tier: `gpt-4o-mini` / `claude-haiku-4.5` / `gemini-3.5-flash`
- 主基准构造者：第四家厂商（不在被测池内）；R2 构造者：`claude-opus-4.8`；verifier/auditor：`gpt-5.6-sol`（强制 per-item family separation）
- 独立性协议：主条件下 agent 之间**无消息传递**。

### 输出

- 每个 agent answer 的解读标签 L_i ∈ {I₀, I₁, …, I⊥}
- 主指标 **CD**（convergent delusion）= (1/N)·max over I_j∉{I₀,I⊥} |{i: L_i=I_j}|，即落在**单一模态错误解读**上的 agent 比例
- 依赖度量：pairwise wrong-agreement、Fleiss' κ、ICC ρ̄、n_eff = n/(1+(n−1)ρ̄)
- 弃权/澄清请求率（规则式非 LLM 检测器）

### 核心流程

1. 构造 reversed items：让"无知求解者的自然默认"成为 **foil**，每个 foil 与 I₀ 仅在**一个约定轴**上不同（如 calendar vs fiscal quarter、floor // vs truncate-toward-zero、闭区间 vs 开区间天数）。
2. 经验默认检查（default check）：确认强模型在无外部信息时确实产出该 foil；H2 项确认可从 prompt 内推出 I₀。54/54 通过。
3. 冻结预注册（假设、指标、决策规则、robustness nulls 全部 git-commit）。
4. 跑 confirmatory run：5,832 个聚合 job，16,461 次 agent 执行，3 个无碰撞种子。
5. 可执行 checker 打标签 → 计算 CD 与依赖度量 → TOST 等价性检验（margin 0.15 / 0.10）。
6. 控制项：R1a（同一基任务 k=0 对照）、R1b（interpretation-uniform null）、R2（跨家族构造）、Amdt14 未筛选样本、regime×domain 交互。


### 方法流程图（文字版）

```
基任务 (含全部消歧子句)  
        │  
        ├── k=0 保留 ──────────────► 广播给 k 个 agent ──► executable check ──► CD ≈ 0.00  
        │  
        └── 删除 1..3 个决定性子句  
                     │  
             ┌───────┴────────┐  
             │                │  
   H1_external            H2_derivable  
 (消歧线索在 prompt 外)   (消歧线索仍在 prompt 内)  
             │                │  
      共享 lossy 表征     可从保留内容推导  
             │                │  
   所有 agent 同一默认      解读分散/正确  
             │                │  
      CD ≈ 0.53           CD = 0.00  
   ρ=0.89, n_eff=1.10     I⊥ 最高 15.2%  
   abstention 0.03%       abstention 0.32%  
             │  
        「5/5 agree」但全错（静默）
```

## Study 2：LPP 检测器

### 输入

同 54 项（executable gold-ambiguity 标签：33 AMB+ / 21 AMB− / 0 非判别）；6 个模型（3 家族 × 2 层）；≥3 seeds。

### 输出

- H_seed（同 prompt 重采样的语义熵，baseline）
- H_ctx-self（前提钉住后答案簇的熵，检测量）
- 二元 flag、AUROC、precision/recall、danger mass、localization

### 核心流程

1. **Self-surface**：通用 prompt 让模型列出"一个称职求解者必须先固定的决策相关未言明假设"，绝不提及目标解读/被删约定/枚举 foil（anti-leakage）。
2. **Counterfactual pin**：对每个自曝维度，钉到**模型自己给的**候选值 v₁…v_m，各产生一个答案。
3. **Executable cluster**：用冻结 harness 的成对等价检查聚类（浮点 tol 1e−9、bool 类型敏感、int 精确、union-find）；不可解析的排除；<2 个可解析答案则 H_ctx-self=0。
4. **Flag**：H_ctx-self > τ=0 ∧ H_seed ≤ τ_s=0.5 bits。
5. **干预（Phase 2b）**：把 flag 当作澄清 gate；被 flag 的 item 由 simulated-user oracle 补上被删轴的 gold 约定，再重跑，用同一 CD labeler 打分。


### 方法流程图（文字版）

```
Underspecified prompt  
↓  
[1] Self-surface latent premises  ── "quarter? rounding? date range?"  
↓  
[2] Pin each premise to model's own candidate values  → answer_v1, v2, v3  
↓  
[3] Cluster answers by EXECUTABLE equivalence (not LLM judge)  
↓  
H_ctx-self = entropy over clusters  
↓  
[4] Flag iff  H_ctx-self > 0  AND  H_seed ≤ 0.5 bits   ← danger quadrant  
↓  
┌──────────────┴──────────────┐  
│                             │  
Detection: AUROC 0.895      Gate: ask user  
(vs SE 0.581)                    ↓  
oracle supplies convention  
↓  
CD 0.626 → 0.010（上界）
```

## 方法依赖

该方法成立依赖以下条件：

1. **存在可执行、确定性的正确性判据**（代码/数值任务）。开放式生成、主观任务无法直接套用。
2. **解读空间可枚举**：I₀ 与 foil 必须事先穷举且互相可区分；论文自己有 2 个 foil set 不完备的 item 落入 I⊥。
3. **消歧轴是单维、离散、可"钉住"的约定**（财年起点、除法约定、区间闭合性）。连续的、隐式的、或多轴纠缠的歧义未测。
4. **模型具备自曝假设的能力**：LPP 第 1 步依赖模型自己能说出相关前提；弱模型上 over-clarification 显著升高（pooled 0.402 vs gpt-5.6-sol 0.032）。
5. **agent 间无通信**（主条件），否则 ICC 的解释会混入社会影响。
6. **交换性**用于 n_eff 的解析；异质 agent 只是近似满足。
7. **oracle 可得**：H-B2′ 的近乎清零结论只在"被删约定仍被回路中某人掌握"时成立。


---

# 实验拆解（Experiments）

## 实验目标

1. 证明收敛性错误由**消歧子句的位置**驱动，而非任务难度、模型能力或厂商同质性（RQ1/RQ3）。
2. 量化名义 k-agent 集成实际提供多少**独立判断**（RQ2）。
3. 证明失效是**静默的**（无弃权/澄清）。
4. 排除"构造者先验共享"和"筛选造成的膨胀"两个致命 confound。
5. 证明该风险可在推理时被黑盒检测，且现有 SOTA 在此象限失明（RQ5）。
6. 证明检测可转化为可行动的澄清 gate。


## 实验设置

### 数据集


| 名称                                                                                                                            | 用途                            |
|-----------------------------------------------------------------------------------------------------------------------------------|-----------------------------------|
| 54 项 executable-gold 基准（40 H1_external + 14 H2_derivable），k∈{0,1,2,3}                                               | 主 confirmatory run              |
| 三域：code_spec（跑测试）、data_analysis（比对计算结果）、policy_qa（`{"amount": float}` 精确到分匹配） | 域泛化 / regime×domain 检验 |
| R2 held-out 子集（12 项，Anthropic 构造）                                                                                 | 跨家族构造控制             |
| 两个 secondary-robustness sidecar（64 项，合计 130/130 认证，163 测试通过）                                        | 稳健性                         |
| Amdt-14 未筛选样本（24 个 k=1 item，无 default screen）                                                                 | 筛选膨胀上界                |
| 71/71 个歧义 item 各配一个 k=0 fully-specified 对照                                                                      | 内项因果对照（R1a）       |


### 模型


| 模型                                                     | 作用                                                                 |
|------------------------------------------------------------|------------------------------------------------------------------------|
| `gpt-5.4`                                                  | 同质单模型基线 / 异质池成员                                |
| `claude-sonnet-4.6`, `gemini-3.1-pro-preview`              | 异质跨家族池                                                     |
| `gpt-5.6-sol`, `claude-opus-4.8`, `gemini-3.1-pro-preview` | 推理层（能力检验）                                            |
| `gpt-4o-mini`, `claude-haiku-4.5`, `gemini-3.5-flash`      | 弱层（能力检验）                                               |
| 第四厂商前沿 code 模型                             | 主基准构造者（在被测池外，做 provenance 分离）        |
| `claude-opus-4.8`                                          | R2 构造者（只在非 Anthropic 模型上计分）                  |
| `gpt-5.6-sol`                                              | verifier / auditor（per-item family separation，不评自家 item） |


### Baseline


| Baseline                                                                                      | 对比目的                                            |
|-----------------------------------------------------------------------------------------------|---------------------------------------------------------|
| single-agent（单模型一次）                                                             | 聚合是否带来增益（H1a）                       |
| self-consistency k=5 / k=10（同模型重采样多数）                                     | 重采样是否恢复独立性                          |
| homogeneous majority N=5（同厂商 5 个）                                                 | ρ→1 的下界参照                                  |
| heterogeneous cross-family aggregation                                                        | 真实"跨厂商比较"界面的最强类比            |
| independence-calibrated counterfactual（按各 agent 自身边际准确率独立重采样） | 剥离"共享题目难度"                              |
| semantic entropy H_seed [15]                                                                  | Study 2 的 SOTA 检测基线                           |
| self-consistency-gated                                                                        | 澄清 gate 基线                                      |
| requirements-probing（只自曝假设，不做 pinning）                                    | **内部 ablation**：pinning 到底加了多少        |
| always-clarify                                                                                | 平凡上界（net=0 by construction）                 |
| token-logprob                                                                                 | 因 Anthropic/Google 不暴露 logprob 而**未报告** |
| cross-vendor synthesis / role-diversified workflow（post-hoc exploratory）                  | 换厂商/换角色能否救                            |


### 指标


| 指标                             | 含义                                                                                                     |
|------------------------------------|------------------------------------------------------------------------------------------------------------|
| **CD**（convergent delusion）    | 落在单一模态**错误枚举解读**上的 agent 份额；I⊥ 计入分母但不能作为收敛标签 |
| CD(parseable) / drop-I⊥          | 两个预注册敏感性变体                                                                             |
| I⊥ rate                          | 离轴/不可解析比例                                                                                  |
| pairwise wrong-answer agreement    | 错误 agent 对中落在同一错误标签的比例（model-free）                                       |
| Fleiss' κ                         | 多评者一致性                                                                                         |
| ICC ρ̄                           | 单因素随机效应模型下"错误指示变量"的组内相关                                          |
| **n_eff = n/(1+(n−1)ρ̄)**      | 名义 n-agent 集成实际提供多少独立判断                                                        |
| Δ = CD_obs − E[CD_indep]        | 超出独立基线的收敛量                                                                             |
| abstention / clarification rate    | 规则式（非 LLM）检测的静默程度                                                                |
| AUROC vs executable gold-ambiguity | 检测器判别力（cluster-by-task_id bootstrap CI）                                                    |
| danger mass                        | AMB+ 项落在 low-H_seed ∧ high-H_ctx 象限的比例                                                   |
| localization                       | argmax-H_ctx 维度与真实被删轴一致的比例                                                       |
| Appropriate / Over / Net / Danger  | 澄清 gate 的适当触发率、过度触发率、净值、危险子集覆盖                             |


---

# 关键实验结果

## 实验A：F1 —— 位置而非难度（R1a 内项对照 + regime 主效应）

### 发现

- 同一基任务：k=0 保留全部消歧子句 → **CD = 0.00**；删除 ≥1 个 → **CD = 0.82**（差值 95% CI [0.73, 0.90]），pipeline、labeler、指标完全相同。
- 宽泛 regime 对比：H1_external CD = **0.53**（可解析答案中 0.60）；H2_derivable CD = **0.00**（各 class 全为 0.000）。
- 效应是 **k≥1 的阈值**而非剂量响应：k>1 后 CD 反而下降，因为 foil 空间变大、I⊥ 率上升稀释了模态错误份额。
- regime×domain 交互 −0.099 [−0.219, 0.014]，不显著 → 非单一域产物（但每域每 cell 仅 n=4）。

### 结果意味着什么

失效被定位在**信息边界**而非模型能力或题目难度。同一题、同一评分器，只切换一个子句就能开关整个现象——这是全文最强的因果证据。

### 是否真正支持作者结论

**强支持**（针对"位置驱动"这一主张）。但对"H1 vs H2 是两个
regime"的宽泛对比只能算**部分支持**：作者自己承认 40 个 H1 与 14 个 H2 是**不同 item family，不是配对最小变体**，构造配对变体被列为 future work。H2 的 CD=0.00 也要窄读——不是"完全解决"，H2 某些 cell 的 I⊥ 率高达 15.2%。

## 实验B：F2 —— 多样性不等于独立性（TOST 等价性）

### 发现

- 各 model class 在 H1_external 上 CD 几乎相同：homogeneous 0.536 / heterogeneous 0.544 / reasoning 0.539 / weak 0.517。
- 异质 vs 同质 ΔCD = −0.003 [−0.078, +0.058]（**与预测方向相反**）。
- Post-hoc TOST：cross-family 与 homogeneous 在 ±0.15（p<0.001）和 ±0.10（p=0.0007）均等价；reasoning vs weak 在两个 margin 均等价（p=0.006）；**weak vs heterogeneous 在 ±0.10 不等价（p=0.145）**——作者主动标出而非掩盖。

### 结果意味着什么

"换厂商 =
换视角"的产品直觉被证伪：共享先验横跨模型家族。这也是把失效归因于**信息边界**而非任何单一模型的关键一步——**null 结果在这里是承重的**。

### 是否真正支持作者结论

**强支持**，且 TOST 的使用方法学上正确（非显著≠等价）。唯一瑕疵：TOST 是 post-hoc secondary，且跑在 method-matched paired item-level
估计（ΔCD=−0.020）而非冻结的 pooled row-35
参考值上——这是一次事后的分析口径切换，作者披露了但仍是自由度。

## 实验C：F3 —— 五个 agent，一个有效判断

### 发现

- H1_external：pairwise wrong-agreement = **0.98**，Fleiss' κ = **0.97**，ICC = **0.89**，**n_eff = 1.10**（名义 ≈8.1）。
- 独立性校准反事实：CD_obs − E[CD_indep] = **+0.245** [0.234, 0.257]。
- self-consistency k=10：n_eff 仍 1.10，ICC 0.91 → **翻倍集成不恢复独立性**；因 ρ̄≈0.89，n_eff 解析饱和于 1/ρ̄≈1.12。
- 预注册的 aggregation-vs-single（H1a）**inconclusive**——作者解释为 k=5 时集成早已塌缩。

### 结果意味着什么

"加更多模型"在结构上无效，这不是采样噪声而是解析上界。这直接否定了多模型界面的核心卖点。

### 是否真正支持作者结论

**强支持**。三个互补估计量（model-free 的 pairwise/κ + 模型化的 ICC + 反事实 Δ）方向一致，交换性假设的弱点被 model-free
指标兜住。唯一保留：n_eff 的"≈8.1 名义"是 pooled mean nominal
ensemble，与摘要里"5 agents"的叙述口径不完全一致，读者容易混淆。

## 实验D：F4 —— 自信且静默

### 发现

- H1_external 弃权/澄清率 **0.031%**，H2 为 0.323%，而 H1 CD = 53.2% → **约 3 个数量级的落差**。
- 剂量假设 H1b **不成立**：线性系数 0.31 [0.18, 0.45] 为正，但完全由 k=0→1 那一步驱动。

### 结果意味着什么

系统内部没有任何自发警报，用户看到的界面与真正的独立佐证**在显示上不可区分**——这正是 Study 2 存在的理由，也是设计含义的落点。

### 是否真正支持作者结论

**部分支持**。数字极其醒目，但"agent 是否 flag
了缺失"由**规则式检测器**判定，作者明说其**人工验证是 future work**。规则式检测器可能漏掉软性对冲表达（"assuming a calendar year…"）——如果模型其实在正文里声明了假设只是没走结构化 abstention 通道，"静默"的强度会被高估。这是全文我最想追问的一点。

## 实验E：F5 —— 不是构造者先验的产物（R2）

### 发现

- 用 Anthropic 重建 trap，只在**非 Anthropic** 模型上计分：single-agent **CD = 0.72**（construct-valid item 上 0.87）。
- 每项跨模型标签集中度（k≥1 层）= 0.711（item-level bootstrap [0.400, 0.978]）；6 项中有 4 项至少两个不同非 Anthropic 家族落在**同一具体 foil** 上。
- 含 6 个 k=0 对照的 all-item 聚合为 0.356 [0.117, 0.622]（k=0 项按设计集中度为 0）。
- 预注册的 R2 aggregation-amplification 指标 **inconclusive**，作者转而依赖 per-item concentration 与 single-agent persistence。

### 结果意味着什么

效应不是"被测模型与构造者共享先验"的伪影，从第二个方向堵住了最致命的 confound。

### 是否真正支持作者结论

**部分支持**。方向对、数字大，但：(a) 仅 12 项子集、k≥1 层只有 6 项；(b) 95% CI [0.400, 0.978] 极宽；(c) 预注册指标失败后改用 post-hoc secondary
指标下结论——这是典型的可被审稿人攻击点，作者披露得很坦白但性质不变。

## 实验F：Study 2 检测（AUROC）

### 发现

- LPP H_ctx-self pooled AUROC **0.895** [0.815, 0.966]；semantic entropy H_seed **0.581** [0.484, 0.675]；ΔAUROC = 0.314（预承诺 ≥0.15）。
- 每模型：H_ctx-self 0.856–0.887，H_seed 0.551–0.606，6 模型/3 家族/2 层完全一致。
- **requirements-probing 已达 0.810**；pinning 增量 **+0.085** [0.01, 0.19]（配对 cluster bootstrap，不含 0）。
- Item 级：33 个 AMB+ 中 \*\*25 个（0.758）\*\*落在 danger quadrant（预承诺 ≥0.40）。
- 冻结操作点：precision 0.926，recall 0.758，k=0 FP 0.095。
- **localization 仅 0.36**：能说"这里有隐前提"，说不准"是哪个轴"。
- token-logprob baseline 因 Anthropic/Google 不暴露 logprob 而**未报告**。

### 结果意味着什么

问题不在"更好的重采样统计量"，而在**换轴**。这是本文最有转化价值的一句话。

### 是否真正支持作者结论

"semantic entropy 在此象限失明" → **强支持**（跨 6
模型一致，且这是构造上必然的）。"LPP 是主要贡献" → **支持不足**：0.810 vs 0.895 意味着一个一行的
prompt（"列出你的隐含假设"）就吃掉了绝大部分信号。作者自己在正文和摘要里都承认了这点，诚实但削弱了方法贡献的分量。另需注意：0.581 的"near-chance"是在**本文构造的 items** 上——这些 item
按设计就是"自信且稳定"的，等于把 baseline
放在它必输的场地上比赛。这不算作弊（作者明说是 by construction），但 ΔAUROC=0.314 不能被读作 semantic entropy 的一般性缺陷。

## 实验G：Study 2 干预（澄清 gate + oracle）

### 发现


| Policy                 | Appropriate | Over  | Net       | Danger    |
|------------------------|-------------|-------|-----------|-----------|
| LPP-gated（ours）    | 0.741       | 0.402 | **0.339** | **0.741** |
| always-clarify         | 1.000       | 1.000 | 0.000     | 1.000     |
| semantic-entropy-gated | 0.140       | 0.024 | 0.116     | 0.140     |
| self-consistency-gated | 0.140       | 0.024 | 0.116     | 0.140     |
| requirements-probing   | 0.975       | 0.881 | 0.094     | 0.975     |


- Net 0.339 [0.201, 0.465]，高于所有 baseline。
- **选择性强烈依赖模型**：`gpt-5.6-sol` 上 over=0.032、net=0.544；池入弱模型后 over 升到 0.402，per-model net 跨度 0.149–0.544。
- H-B2′ oracle：AMB+ 上 CD 从 **0.626** [0.490, 0.763] 降到 **0.010** [0.000, 0.025]（配对降幅 0.616 [0.480, 0.753]），I₀ 命中 94.1%；6 个模型中 5 个 oracle CD = 0.000。
- 全部 972 个 run cell 池化到 54 项；committed answer 温度 0.0。

### 结果意味着什么

"检测 → 澄清 → 解决"链路在**理想条件下**是完整的；同时 requirements-probing 的 net
崩塌（over=0.881）说明**过度澄清是真实的可用性代价**，简单方案在部署上并不划算。

### 是否真正支持作者结论

**部分支持**。0.626→0.010 数字惊人，但它是 **simulated-user oracle 直接喂 gold
约定**——这几乎是把答案递给模型。而全文的叙事恰恰是"这个约定在上游 handoff 中丢了"，所以键盘前的人多半也不掌握它；再加上 localization 仅 0.36，detector
自己不知道该问什么。作者三次明确标注为上界并自陈这一张力，处理是我见过的比较诚实的，但结论的实用射程被限制在"约定仍可恢复"这一子集内。此外 pooled over-clarification 0.402 意味着**每 5 次无歧义请求就有 2
次被打断**，在真实产品里这个 gate 大概率不可接受。

---

# 最重要的 Figure 和 Table

## Figure 1（Overview，p.2）

- **表达什么**：H1/H2/H3 三块并置——相同界面显示 "5/5 models agree"，但一侧 CD≈0.53、n_eff=1.10，另一侧 CD=0.00。
- **为什么重要**：一张图讲完全文因果结构，并且明确标注"identical display"——把技术发现直接接到界面问题上。
- **核心结论**：显示完全相同，证据价值相差一个数量级；correctness 由可执行检查而非 LLM judge 判定。

## Table 4（CD by regime × model class，p.12）

- **表达什么**：4 个 model class × 2 个 regime 的 CD、CD(parseable)、I⊥ rate。
- **为什么重要**：**能力 null 与 regime 主效应在同一张表里**，一眼看到 0.517–0.544 的近乎恒定与 0.000 的整列。
- **核心结论**：变的是位置（0.53 vs 0.00），不变的是能力（跨 class 差异不可检测）。同时暴露 H2 的 I⊥ 最高 0.152——CD=0 要窄读。

## Table 5 + Figure 3（依赖度量，p.13/14）

- **表达什么**：pairwise 0.98 / κ 0.97 / ICC 0.89 / n_eff 1.10 / Δ +0.245。
- **为什么重要**：把"伪冗余"从修辞变成可测量的数：名义 ≈8.1 → 有效 1.10。
- **核心结论**：加 agent 不加证据；观测到的收敛显著超出同等准确率下独立 agent 会产生的量。

## Figure 5 + Figure 7（danger quadrant 与 AUROC，p.17/19）

- **表达什么**：Fig.5 把 54 项画在 (H_seed, H_ctx) 平面上，阴影区 25/33 AMB+；Fig.7 是每模型与 pooled 的 AUROC 柱，含 requirements-probing 参考线。
- **为什么重要**：Fig.5 是全文最有说服力的"机制可视化"——SOTA 失明的区域被直接画了出来；Fig.7 则同时展示了主结果和**削弱主结果的 ablation**（0.810 参考线）。
- **核心结论**：危险不是波动而是稳定；换轴有效，但换轴的大部分收益来自"问一句假设"。

## Table 9（干预策略对比，p.21）

- **表达什么**：5 种澄清策略的 Appropriate / Over / Net / Danger。
- **为什么重要**：唯一展示**可用性代价**的表；always-clarify 的 net=0 与 requirements-probing 的 over=0.881 说明"多问"不是免费的。
- **核心结论**：LPP 在净值上赢，但 over=0.402 的绝对水平仍然是产品级障碍。

（补充值得看：**Table 10** 威胁-控制对照表，把 5
个主要反驳与对应证据一一列出，是审稿友好度极高的写法；**Table 6** 完整报告了包括 Not supported / Not estimable 在内的所有预注册结果。）

---

# 论文局限性（Limitations）

## 数据局限

- **54 项，其中 H2 仅 14 项**——H2 侧所有结论（包括 reasoner×capability 交互不可估计）都受制于此。
- **items 是机器构造的合成 trap**，非自然发生的 handoff 丢失样本；生态效度未测。
- **入选条件依赖于随后被测量的行为**（unaware 模型必须产出预定 foil）——采样框与因变量部分耦合。未筛选复制只有 24 项 k=1，CI [0.521, 0.839] 很宽。
- **三域覆盖窄**且 policy_qa 只验证最终数值不验证推理路径；regime×domain 检验每 cell 仅 n=4。
- R2 子集 12 项，k≥1 层只有 6 项，跨模型集中度 CI [0.400, 0.978] 宽到几乎不排除任何东西。
- 两个 item 的 foil set 不完备（模型达到未枚举解读 → I⊥）。

## 方法局限

- **CD 指标的结构性偏差**：k 增大时 foil 空间变大、I⊥ 上升，会**机械地稀释**模态错误份额。作者承认这解释了非单调性，但也意味着 CD 在不同 k 之间**不可直接比较**，"阈值而非剂量"这一结论有一部分是指标性质而非现象性质。
- **ICC / n_eff 依赖交换性**，异质家族并不严格满足；虽有 model-free 指标兜底，但 n_eff=1.10 这个最抓眼的数字来自最脆弱的估计量。
- "静默"由**未经人工验证的规则式检测器**判定，可能把正文中的软性假设声明误判为"未 flag"。
- 主条件下 agent **零通信**——这与真实多模型产品（有 synthesis、有 debate）不完全一致；debate 只在 exploratory 附录里测。
- LPP 的 self-surface 步骤把负担压在模型自身能力上，弱模型上过度触发率飙升；localization 0.36 意味着 detector 无法自主定位问题。
- **可执行等价聚类**只适用于有确定性输出的任务，不可迁移到开放式生成。

## 实验局限

- **无人类被试**——全文关于"用户会过度信任""dependence-aware 界面会提升澄清行为"的论断都是**推断而非验证**，6 条设计含义全部 untested（作者明说 "we ran no UI study"）。
- 预注册指标失败后改用 post-hoc 指标下结论出现了两次（R2 的 amplification、异质 vs 同质的 TOST 口径）。
- H1a（聚合 vs 单 agent）inconclusive、R1b inconclusive、H1b not supported、H2 交互 not estimable——预注册假设的支持率其实不高，主效应是靠 R1a 单独扛住的。
- temperature 0.0 + 3 seeds 使单项 per-seed CD 分辨率很粗，全靠 item-set 均值与 cluster bootstrap。
- 干预实验用 **oracle** 而非真实用户，且 oracle 直接给出 gold 约定。

## 外部有效性问题

- 只测**单轮、非交互**任务；真实 pipeline 有迭代、有人在环、有工具反馈。
- 只测 3 个厂商 6 个模型的某一时间快照；模型版本迭代很快（gpt-5.4/5.6-sol、claude-4.6/4.8、gemini-3.1/3.5 均为文中 roster）。
- 结论限定在"约定型、离散、单轴歧义"；对**语用歧义、价值判断歧义、多轴纠缠歧义**是否成立完全未知。
- 论文自己放弃 prevalence 主张——所以"现实中这种情况多常见"是**完全开放的**，而这恰恰是设计决策最需要的数字。

## 潜在混杂变量

- **筛选 × 效应量耦合**（已部分处理，但样本小）。
- **预训练分布共享**：所有被测模型可能在相似语料上训练，"共享信息边界"与"共享预训练语料"在本设计中**无法分离**——R2 只排除了与*构造者*共享先验，没排除被测模型之间的先验共享（但这恰恰也是论文想说的，属于构念与混杂的边界模糊）。
- **prompt 措辞效应**：删除子句同时也改变了 prompt 的长度与句法，可能带来"更短 prompt → 更强默认锚定"的次级效应，未单独控制。
- **对齐/指令微调的同质化**（作者在 §2.5 引用了 [18,31,33] 作为机制猜想，但未做实验分离）。
- **Verifier 家族**：verifier/auditor 是 `gpt-5.6-sol`，虽有 per-item family separation，但 OpenAI 系仍同时出现在被测池与审计角色中。

## 未验证假设

- 用户确实会把 "N/N agree" 读作独立佐证（引的是人类顾问文献 [6,13,26]，未在 AI 界面情境验证）。
- dependence-aware 显示会改善依赖校准（6 条设计含义全未评估）。
- "任何不改变共享输入的干预都无法降低 CD"——作者明确标为**可证伪的猜想**，仅有 2 个 exploratory 条件的弱支持。
- 真实用户能补上被删的约定（oracle 的核心前提）。
- 规则式 abstention 检测器与人工判断一致。

---

# 潜在可复现性分析

### 最容易复现的部分

- **构念与度量**：CD 的定义、pairwise agreement、Fleiss' κ、ICC、n_eff 公式（Eq.2）在文中完整给出，任何人都能在自己的数据上重算。
- **danger quadrant 的定性现象**：H_seed 与 H_ctx 的分离，用任意两个 API 模型 + 十几个自造的 convention-trap 题，一个下午能重现方向性结论。
- **requirements-probing baseline**：就是一句 prompt，AUROC 0.810 这个数几乎肯定能复现。
- **k=0 vs k≥1 的内项对照**：设计极简单，是最值得优先复现的一步。
- 作者承诺开源 benchmark items、executable gold-checkers、adversarial-foil validator、分析与运行代码、prompts、model/version 记录、预注册与全部签名修订账本（接受后给永久归档链接）。

### 最困难的部分

- **精确数值复现**：主构造者是"第四厂商前沿 code 模型"，slug 留到 camera-ready；Google slug 还在运行中被 proxy 改名（`gemini-3.1-pro` → `gemini-3.1-pro-preview`）。模型端点漂移会让 0.53 / 0.895 这类点估计无法逐位对齐。
- **default check 的复刻**：入选靠"unaware capable models 产出预定 foil"，这一步依赖当时的模型行为，换一代模型可能整批 item 失效。
- **adversarial-foil validator 的严格性**：fail-closed 语义、`AmbiguousLabelError`、130/130 认证——重建等价的验证器工作量不小。
- **完整规模**：5,832 个聚合 job / 16,461 次 agent 执行 + Phase B(≈1.5k) + Study 2 检测与干预 + A13/A14 稳健性运行。作者用机构托管 proxy 跑出 $0，独立复现者要按 API 市价付费。
- **规则式 abstention 检测器**：文中只说"rule-based (non-LLM)"，具体规则未在正文给出。

### 缺失哪些关键信息

1. 主构造者模型的具体身份（"fourth vendor"，slug 待 camera-ready）。
2. self-surface prompt、pin prompt 的**原文**（正文只有语义描述；据称在 artifact 中）。
3. abstention 检测器的规则集与其误判率。
4. 54 项 item 的完整清单与每项的 I₀/foil 轴（正文只有 Table 2 的 4 个例子）。
5. Appendix A/B/C（预注册全文、签名修订账本、exploratory Phase B、regime×domain）在本 PDF 中被引用但正文未展开。
6. per-item 原始标签矩阵——没有它，ICC/n_eff 无法被第三方重算。
7. 采样温度（committed answer 是 0.0，但 semantic entropy 的重采样温度与 k 未在正文明示）。


### 预计风险


| 风险                                             | 等级  | 说明                                                        |
|----------------------------------------------------|---------|---------------------------------------------------------------|
| 模型版本漂移导致 default check 失效      | **高** | 整个 item set 的构念效度绑定在特定模型代次上 |
| 点估计不可复现（0.53 / 0.895）            | 中高  | 方向性大概率保住，数值几乎肯定偏移           |
| API 成本                                         | 中     | 无机构 proxy 时数万次调用是真实开销             |
| prompt 未公开导致 LPP 无法等价实现      | 中     | 但 requirements-probing 变体极易近似                   |
| H2 侧结论（14 项）不稳定                  | 中     | 小样本，换 item 可能出现非零 CD                    |
| n_eff 的交换性假设在别的 roster 上崩掉 | 中     | 建议同时报告 model-free 指标                          |


---

# Future Work

（前 3 个是作者自陈；后续为从内容推导）

1. **人类被试研究（作者自陈）**：约 50 人被试内设计，测跨模型一致性是否提高采纳率、是否在共享错误解读时造成过度依赖、dependence-aware 界面是否提升澄清行为。2. 价值：全文 6 条设计含义目前**零验证**，这是把 computational finding 变成 CSCW 论文的必要一步。难度：**中**（需 IRB，但设计成熟）。
3. **输入/证据多样化干预的预注册确证实验（作者自陈）**：retrieval-diverse / context-diverse 条件，替代目前 post-hoc 的 synthesis 与 role-diversified。
4. 价值：直接检验"只有多样化**输入**才有用"这一可证伪猜想。难度：**中**。
5. **构建并评估 dependence-aware 多模型界面（作者自陈）**：把 shared input / context completeness / common interpretation / alternative interpretation / recommended action 五要素做成真实面板。
6. 价值：唯一能把论文变成系统贡献的路径。难度：**中高**。
7. **配对的 H1/H2 最小变体 item**（作者点名为 future work）：同一 item 在两个 regime 下都发布。
8. 价值：消除"不同 item family"这一最大构念反驳。难度：**低**。
9. **Phase 2c AU-Probe 白盒对照**（已预注册但本文未跑）：白盒探针 vs 黑盒 LPP。
10. 价值：说明黑盒相对内部信号损失多少。难度：中（需开源权重模型）。
11. **abstention
检测器的人工验证**（作者自陈）：核心"静默"主张目前靠规则匹配。
12. 价值：F4 是全文最抓眼的数字之一，验证成本低、回报高。难度：**低**。
13. **prevalence 研究**：在真实 agent pipeline / 工单 / handoff 日志中估计欠规范 handoff 的实际发生率。
14. 价值：把"failure mode"升级为"failure rate"，是决定这项工作是否重要的关键数字。难度：**高**（需真实企业数据）。
15. **多轮交互与人在环设置**：目前全部是单轮非交互。
16. 价值：真实系统都是多轮，澄清可能在第二轮自然发生。难度：中。
17.
**歧义类型扩展**：从"离散约定轴"扩展到语用歧义、指代歧义、价值/规范歧义、多轴纠缠。
18. 价值：决定该现象的边界。难度：**高**（可执行金标准会失效，需要新评测范式）。
19. **LPP 的定位能力**（localization 0.36 → ?）：从"有隐前提"到"是哪个前提"。
20. 价值：不解决定位，澄清 gate 就问不出具体问题，端到端价值受限。难度：**中高**。
21. **过度澄清的成本-收益建模**：over=0.402 在什么任务价值下是划算的？
22. 价值：产品可部署性的门槛问题。难度：低（可做理论/仿真）。
23. **训练时干预**：能否通过 RLHF/SFT 提高"遇到欠规范就
flag"的倾向而不牺牲有用性？
24. 价值：从界面补丁转向根因。难度：**高**。
25. **provenance-preserving handoff 协议**：在 agent pipeline
里携带"哪些约定已被固定"的元数据。
26. 价值：论文把问题定位在 pipeline，这是对应的系统解。难度：中高。
27. **fleet-level 解读单一栽培审计**：跨模型舰队的解读集中度指标与监控。
28. 价值：对应设计含义 (6)，也接 algorithmic monoculture 文献。难度：中。


---

# Follow-up Research Ideas

## 容易发表的小改进（5 个，workshop / short paper 级）

### S1. 配对 H1/H2 最小变体基准

- **创新来源**：直接补上作者自认的构念缺口（"different item families, not paired minimal variants"）。
- **需要修改什么**：把每个基任务同时实例化为 external 与 derivable 两版，只改一句话的位置。
- **实验设计**：同 roster、同 checker，within-item 2×2（regime × k），配对 t / 混合效应模型。
- **预期贡献**：把 regime 主效应从"宽泛比较"升级为"配对因果"，是原论文最容易被攻击点的直接修补。

### S2. abstention 检测器的人工验证 + 软性对冲编码

- **创新来源**：F4 的"3 个数量级落差"目前只有规则式证据。
- **需要修改什么**：对全部 16,461 条响应做分层抽样人工编码，区分"结构化弃权""正文软性假设声明""完全沉默"。
- **实验设计**：2 名编码者 + Cohen's κ；报告规则式检测器的 precision/recall。
- **预期贡献**：可能**修正**原结论——如果模型其实经常在正文里说"assuming calendar year"，那么问题从"模型不说"变成"界面不显示"，设计含义随之改写。这个反转本身就是可发表的。

### S3. CD 指标的去偏版本

- **创新来源**：CD 随 foil 空间与 I⊥ 率机械稀释，导致 k 间不可比。
- **需要修改什么**：定义按 foil 基数归一化的 CD′，或直接用"错误标签分布的归一化熵/HHI"。
- **实验设计**：在作者释出的原始标签矩阵上重算，比较 CD 与 CD′ 的 k-曲线。
- **预期贡献**：一个更干净的度量 + 对"阈值 vs 剂量"结论的再检验。

### S4. 温度/采样与 prompt 措辞的敏感性研究

- **创新来源**：committed answer 全在 T=0；prompt 删除子句同时改变了长度与句法。
- **需要修改什么**：加入温度扫描（0/0.3/0.7/1.0）与"长度匹配的安慰剂删除"（删掉一句无关子句）。
- **实验设计**：3×4 网格，观察 CD 与 n_eff 是否随温度上升而衰减。
- **预期贡献**：分离"共享先验"与"贪心解码"两种收敛来源——如果 T=1 下 CD 大幅下降，原结论的解释就要改。

### S5. requirements-probing 的极简版基准化

- **创新来源**：0.810 vs 0.895 的 ablation 说明简单方案已经很强。
- **需要修改什么**：系统化比较 5–8 种"自曝假设"prompt 变体的 AUROC / over-clarification 成本。
- **实验设计**：同 54 项 + 一批新构造项，报告 Pareto 前沿（覆盖率 vs 打扰率）。
- **预期贡献**：给出实际部署时的"最便宜可用信号"，实用价值可能高于 LPP 本身。

## 中等规模扩展（5 个，full paper 级）

### M1. Dependence-Aware Consensus Panel：构建 + 被试内实验

- **创新来源**：作者的设计含义 (1)(2)(3) 全部 untested。
- **需要修改什么**：实现一个真实的多模型界面，三臂对比：`N/N agree` 徽章 / 仅显示分歧 / 完整依赖面板（shared input、context completeness、common interpretation + alternative、recommended action）。
- **实验设计**：约 60–90 人被试内，任务混入 H1 陷阱题与正常题；测量采纳率、澄清发起率、over-reliance（在共享错误解读上的接受率）、以及**过度澄清导致的任务耗时**。
- **预期贡献**：把 computational finding 转成 CHI/CSCW 的实证 + 系统双贡献，这是本论文最自然、最高回报的续作。

### M2. 输入多样化 vs 厂商多样化的确证实验

- **创新来源**：作者明确写成"falsifiable conjecture：任何不改变共享输入的干预都不该降低 CD"。
- **需要修改什么**：新增条件——retrieval-diverse（不同检索路径）、context-diverse（不同上下文重写）、persona-diverse（不同任务框架），与 vendor-diverse、role-diverse 对照。
- **实验设计**：预注册，5 条件 × 54+ 项 × 3 seeds，主指标 CD 与 n_eff；预测只有前两者能把 n_eff 推离 1。
- **预期贡献**：**证伪或坐实**论文的核心机制主张，理论价值高于任何检测器改进。

### M3. LPP 的定位化（Localized LPP）

- **创新来源**：localization 0.36 是端到端链路的瓶颈。
- **需要修改什么**：把 pinning 从"整体熵"改为**逐维归因**（类似 Shapley / 逐轴消融），输出"最可能缺失的是财年起点"而非"这里有歧义"。
- **实验设计**：在 33 个 AMB+ 项上测 top-1/top-3 定位准确率；并做端到端 gate 实验——定位化 gate 的澄清问题质量（能否让真实用户回答）。
- **预期贡献**：让 detector 从"报警器"变成"提问器"，直接提升 H-B2′ 的现实射程。

### M4. 真实用户替代 oracle 的澄清实验

- **创新来源**：0.626→0.010 完全依赖 oracle 直接喂 gold。
- **需要修改什么**：把 simulated-user 换成真人，且**故意设置三种知识条件**：用户掌握约定 / 用户不掌握但能查 / 约定真的丢失。
- **实验设计**：3×2（知识条件 × 有无 gate），主指标 CD 与任务完成时间。
- **预期贡献**：给出"clarification gate 的现实收益曲线"，把上界替换成期望值。这是原论文最大的悬空处。

### M5. 生态样本上的 prevalence 研究

- **创新来源**：作者主动放弃 prevalence。
- **需要修改什么**：从真实 agent pipeline / 客服工单 / 代码 issue handoff 中挖掘自然发生的欠规范请求，人工标注是否存在决定性缺失约定。
- **实验设计**：分层抽样 + 双标注；在自然样本上跑同一 roster 测 CD。
- **预期贡献**：把 failure **mode** 升级为 failure **rate**——决定这条研究线值不值得整个社区投入。

## 具有较强创新性的方向（5 个）

### L1. 证据独立性的可计算理论：从 n_eff 到"信息边界熵"

- **创新来源**：n_eff 只是 ρ 的函数，它测的是**结果相关**，不是**证据独立**。真正需要的是"这 k 个答案共同依赖的信息量"这一量。
- **需要修改什么**：定义一个 estimand——给定一组 agent 的答案分布，估计其共同条件变量的维度/熵（可借鉴 common-information / Wyner common information 或 partial information decomposition）。
- **实验设计**：在可控合成环境（已知共享 context 比例）中验证估计量的可辨识性，再迁移到 LLM ensemble。
- **预期贡献**：给 CSCW/ML 一个**通用的"聚合何时有认识论价值"判据**，适用范围远超 LLM——这是把本论文从"一个现象"升级为"一个理论工具"的路径。难度高，回报也最高。

### L2. Interpretive Monoculture Index：舰队级审计指标与监管接口

- **创新来源**：设计含义 (6) 只有一句话；FAccT 侧完全空白。
- **需要修改什么**：定义跨模型、跨版本的"解读集中度"指标，随时间追踪（对齐调优是否在加剧单一栽培？）。
- **实验设计**：对同一 item set 跑多代模型（历史 checkpoint），画集中度的时间序列；与 [18,31,33] 的输出多样性收窄结论对齐。
- **预期贡献**：把 algorithmic monoculture 从系统层（多个决策者用同一模型）下沉到 **ensemble 内部层**，并给出可监管的量化指标。

### L3. 让"沉默"变成可训练目标：underspecification-aware alignment

- **创新来源**：abstention 0.03% 是训练目标的产物（helpfulness 压倒 calibration），而非能力缺陷。
- **需要修改什么**：构造"欠规范 → 应当提问"的偏好数据，做 DPO/RLHF，同时用一个 over-clarification 惩罚项控制打扰率。
- **实验设计**：主指标 = (danger coverage, over-clarification) 的 Pareto 前沿；对照本文的推理时 LPP gate。
- **预期贡献**：回答"这应该在模型里修还是在界面里修"——目前全领域都默认后者，前者基本没人做。

### L4. 从"共识"到"分歧的信息价值"：反转目标函数

- **创新来源**：本文证明 agreement 在欠规范下无信息量；那么**分歧**是否是欠规范的最优指示器？
- **需要修改什么**：不追求 detector，而是**主动制造受控分歧**——给不同 agent 注入不同的前提假设（premise-diversified ensemble），把分歧结构本身作为输出呈现给用户。
- **实验设计**：premise-diversified ensemble vs vendor-diversified vs single；测 CD、danger coverage，以及用户在"看到分歧结构"时的决策质量。
- **预期贡献**：把检测问题转成**生成问题**——不是事后报警，而是让 ensemble 在设计上就跨越信息边界。这条线同时是 NeurIPS-able（方法）和 CHI-able（界面）。

### L5. 跨模态与跨人机的伪冗余

- **创新来源**：本文只测 LLM 文本任务，但"共享 lossy 表征 → 伪独立"是一般性机制。
- **需要修改什么**：扩展到 (a) 多模态 agent（都看同一张图）、(b) 人–AI 混合团队（人和 AI 读同一份简报）、(c) 多个人类专家读同一份不完整材料。
- **实验设计**：跨三种设置用同一套 n_eff / CD 度量，检验 fake redundancy 是否是"表征共享"的一般后果而非 LLM 特性。
- **预期贡献**：把构念从 LLM 提升为**协作系统的一般性质**，直接对话 hidden-profile / common-knowledge effect 的经典文献 [16,42]，理论野心最大。

---

# 审稿人视角评价

## CHI Reviewer

- **最大优点**：问题选得极好——"N/N models agree"是每天都在发生的真实界面交互，而论文给出了一个干净、可开关的机制解释，Figure 1 的"identical display"把技术发现直接翻译成界面问题。
- **最大缺点**：**没有任何用户**。全文关于信任、依赖、过度依赖、澄清行为的论断都是推断；6 条设计含义作者自己标注"await empirical evaluation"。对 CHI 来说这是致命的缺口。
- **最可能被质疑的问题**：- "你怎么知道用户真的把 5/5 读成独立佐证？"（引的是人类顾问文献，非 AI 界面证据）
- over-clarification 0.402 在真实界面里是不是比原问题更糟？
- 6/9 平台的 landscape audit 是快照式文档编码，能否支撑"这是个普遍的界面问题"？
- **评级**：**2.5 / 5（Borderline，倾向 Reject 但可救）**。加一个哪怕 40 人的被试实验就能到 4.0。

## CSCW Reviewer

- **最大优点**：把问题正确地定位在 **grounding / information boundary** 而非模型——§8.3 对 groupthink 的机制区分（"我们的 agent 不通信却仍收敛"）写得非常好，并且明确指出针对 groupthink 的干预（devil's advocacy、结构化异议）在这里**无效**，因为失效发生在任何交互之前。这是真正的概念贡献。与 hidden-profile / common-knowledge effect [16,42] 的连接（"当决定性事实缺席于**每个** agent 的 prompt 时，已经没有未共享信息可池化"）是全文最漂亮的一段理论工作。
- **最大缺点**：CSCW 的"C"缺失——没有人、没有团队、没有真实 handoff。合成的 trap 与"跨人–工具–agent 的上下文丢失"之间的类比未经任何实证支撑。
- **最可能被质疑的问题**：- 这真的是协作研究，还是一篇被写成 CSCW 语气的 LLM 评测？
- "上游 handoff 丢失约定"在真实组织流程里长什么样？有没有一个 field 观察？
- oracle 干预与论文自身叙事矛盾（丢了的东西用户怎么会有）——这个张力作者承认了，但没解决。
- **评级**：**3.0 / 5（Borderline Accept）**。概念贡献够，实证基础偏薄；如果是 revise-and-resubmit 制度下我会给 major revision。

## FAccT Reviewer

- **最大优点**：把 algorithmic monoculture 从"多个决策者用同一模型"下沉到"一个 ensemble 内部"，是有价值的构念延伸；且指出 correlation neglect **可被利用**（[26]：发出多个相关信号的来源可以随意操纵忽视相关性的受众）——"5/5 agree"徽章正是这种可利用的线索。dual-use 讨论（释放构造程序而非静态排行榜）处理得体。
- **最大缺点**：**没有做危害分析**。没有说明哪些人群、哪些高风险场景（信贷、医疗、移民、司法）会承受这种失效的后果，也没有讨论 gate 的**分配性影响**——over-clarification 0.402 会不均匀地落在谁头上？弱模型上过度触发率更高，意味着用便宜模型的用户被打扰更多，这是个明确的公平性问题却完全没提。
- **最可能被质疑的问题**：- "convergent delusion"这个词是否在给系统赋予不当的心理学隐喻？（作者预先辩护了，但仍会被追问）
- 三个厂商共享先验——这是否意味着基础模型生态的**结构性集中风险**？论文引了 [3] 却没往下走。
- 依赖面板会不会制造新的"合规剧场"（显示了 dependence 就免责）？
- **评级**：**2.5 / 5（Weak Reject）**。诊断有价值，但缺少 FAccT
期待的规范性分析与受影响群体视角。

## NeurIPS Reviewer

- **最大优点**：方法学纪律罕见地好——预注册冻结、签名修订账本、**完整报告 not-supported / inconclusive / not-estimable 的所有结果**、TOST 而非"非显著即等价"、fail-closed 的对抗 foil 校验、跨家族构造分离、以及主动披露 pinning 只贡献 +0.085 的内部 ablation。Table 10 的"威胁—控制—证据"三列表是我希望所有论文都有的东西。
- **最大缺点**：**技术新意不足**。ρ→1 ⇒ n_eff→1 是 ensemble 理论的教科书结论；detector 的主要信号来自"问模型有什么隐含假设"（0.810），真正新颖的 counterfactual pinning 只加 0.085；semantic entropy 的 0.581 是在**按定义对它不利**的构造样本上测得的，ΔAUROC=0.314 不能作为一般性优越性主张。
- **最可能被质疑的问题**：- 54 项、其中 H2 仅 14 项，样本量对 NeurIPS 标准而言太小；R2 的 k≥1 层只有 6 项而 CI 是 [0.400, 0.978]。
- CD 在不同 k 之间因 foil 空间稀释而不可比，"阈值而非剂量"有多少是指标性质？
- ICC/n_eff 依赖交换性，而 roster 明显异质。
- 预注册指标失败后改用 post-hoc 指标（R2 amplification、TOST 口径切换）——虽披露但是自由度。
- 为什么不测开源权重模型？白盒对照（Phase 2c）预注册了却没跑。
- **评级**：**4 / 10（Reject）** 作为方法论文；但若投到 datasets & benchmarks track 或 workshop，凭 pre-registration 质量与 danger quadrant 的概念清晰度可到 **6 / 10（Weak Accept）**。

---

# 最终研究地图

```位置驱动
【问题】  
"N/N models agree" 被当作独立佐证  
  └─ 但聚合的认识论保证要求误差近似独立（Condorcet / ensemble 分解）  
  └─ 同 prompt 广播恰好破坏该前提，界面却不披露（9 平台 audit：输入侧信号 0/9）  
        │  
        ▼  
【机制假设】  
model diversity ≠ evidence diversity  
共享信息边界 → 解读单一栽培（interpretive monoculture）  
        │  
        ▼  
【方法】  
可执行金标准基准（54 项 / 3 域 / k∈{0..3}）  
  ├─ reversed items：自然默认 = foil，单轴差异  
  ├─ 唯一操纵变量：消歧子句在 prompt 内 / 外  
  ├─ 正确性由 check() 判定，无 LLM judge  →「一致」与「正确」定义上分离  
  ├─ 度量：CD + pairwise/κ/ICC/n_eff + 独立性反事实  
  └─ 检测器 LPP：自曝前提 → 反事实钉住 → 可执行等价聚类 → H_ctx-self  
        │  
        ▼  
【实验】  
Study 1（5,832 jobs / 16,461 executions / 3 seeds）  
  F1 位置非难度   同项 k=0→k≥1  ΔCD = 0.82 [0.73,0.90]；regime 0.53 vs 0.00  
  F2 多样性无效   跨 class CD 0.517–0.544；异质−同质 −0.003；TOST 等价 ±0.10  
  F3 伪冗余       pairwise 0.98 / κ 0.97 / ICC 0.89 / n_eff 1.10（k=10 仍 1.10）  
                  独立性反事实 Δ +0.245 [0.234,0.257]  
  F4 静默         abstention 0.031% vs CD 53.2%（≈10³ 倍落差）；H1b 不支持  
  F5 非构造者伪影 R2 跨家族 single-agent CD 0.72；per-item 集中度 0.711  
  未筛选复制      CD 0.685 [0.521,0.839]，不衰减  
Study 2（54 项 / 6 模型 / 3 家族 × 2 层 / 972 cells）  
  检测            LPP 0.895 [0.815,0.966] vs SE 0.581 [0.484,0.675]，Δ 0.314  
                  ablation：requirements-probing 已 0.810，pinning 仅 +0.085  
                  danger mass 25/33；precision 0.926 / recall 0.758 / k0FP 0.095  
                  localization 仅 0.36  
  干预            LPP-gated net 0.339（over 0.402）；oracle CD 0.626 → 0.010  
        │  
        ▼  
【结论】  
失效由信息边界决定，与能力、厂商无关  
k-agent ensemble ≈ 1 个有效独立判断，且无内部警报  
危险信号不是"波动"而是"稳定"→ 检测要换轴，不是换统计量  
设计含义：把「N/N agree」换成 evidential dependence 显示（6 条，全未验证）  
        │  
        ▼  
【局限】  
数据：54 项 / H2 仅 14 / 合成 trap / 入选条件与因变量耦合 / 域窄  
方法：CD 随 foil 空间稀释 → k 间不可比；交换性理想化；静默靠规则检测器  
实验：零人类被试；多个预注册假设 inconclusive；oracle 直接喂 gold  
外效：单轮非交互；单一模型快照；只覆盖离散约定型歧义  
混杂：预训练语料共享无法与"信息边界"分离；prompt 长度未做安慰剂控制  
        │  
        ▼  
【Future Work】  
作者线：人类被试 → 输入多样化确证实验 → 构建 dependence-aware 界面  
外推线：配对 H1/H2 变体 / 定位化 LPP / prevalence 研究 / 训练时干预 /  
        歧义类型扩展 / 舰队级单一栽培审计  
        │  
        ▼  
【我的潜在切入点】（按 投入产出比 排序）  
① S1 配对 H1/H2 最小变体            —— 最低成本补最大构念漏洞，2–3 周  
② S2 abstention 人工验证            —— 有机会得到"反转型"发现（模型其实说了，是界面没显示）  
③ M1 Dependence-Aware Panel + 被试   —— 把本文缺的那一半补上，最自然的 CHI/CSCW 续作  
④ M2 输入多样化 vs 厂商多样化确证    —— 直接检验作者自陈的可证伪猜想，理论回报最高的中型工作  
⑤ L4 premise-diversified ensemble   —— 从"检测"转向"生成"，同时可投 NeurIPS 与 CHI  
⑥ L1 信息边界熵 / 共同信息估计量     —— 把 n_eff 换成真正测"证据独立"的量，野心最大、难度最高
```

**一句话的战略判断**：这篇论文的现象层贡献（ρ→1 ⇒ n_eff→1）对懂 ensemble 的人不新，检测器贡献被自己的 ablation 削弱到
+0.085，真正立得住的是\*\*"位置而非能力"这一可开关的因果轴**加上**罕见诚实的预注册纪律\*\*。它留下的最大空白是**完全没有人**——谁先把 M1（依赖面板 + 被试实验）做出来，谁就拿走这条线上最容易的一篇 CHI/CSCW full paper。

 
