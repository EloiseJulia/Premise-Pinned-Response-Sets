# Premise-Pinned Response Sets · AI-Native 研究工作流

> **用途**：本文件是 Premise-Pinned Response Sets（PPRS）课题的执行规范。它将开题报告中锁定的设计转成 **Spec-Driven Research + Agent Execution + 独立审计 Gate** 流程。
> **课题依据**：[`开题报告-Premise-Pinned-Response-Sets-实施规格.md`](../开题报告-Premise-Pinned-Response-Sets-实施规格.md) 是研究事实、硬约束与偏离判定的唯一来源；任何与其冲突的实现提议都必须先写入偏离日志并由课题负责人确认。

---

## 0. 已锁定的项目配置

下表已为本课题解析。后文的 `<N>`、`<name>`、`<topic>`、`<PR>`、`<date>` 仅为每次任务实例化时填写的 issue、分支、主题、PR 和日期变量。

| 占位符 | 含义 | 示例 |
|---|---|---|
| 项目值 | 本课题取值 |
|---|---|
| 仓库 | `Premise-Pinned-Response-Sets`（GitHub owner：`EloiseJulia`） |
| 主 checkout | `C:\Users\v-elzhang\Desktop\MyFolder\Premise-Pinned Response Sets` |
| 默认分支 / worktree 根目录 | `main` / `.worktrees/` |
| Agent / 计算环境 | GitHub Copilot（本地 Windows 环境）；模型与 provider 快照写入预注册与原始记录 |
| 研究文档 | `docs/specs/`、`docs/plans/`、`docs/research/`、`docs/experiments/` |
| 大型或可再生产物 | 本地 `artifacts/`（git 外）；仅提交配置、代码、清单、摘要哈希与可重建图表脚本 |
| 构建、运行、测试 | 在 Phase 1 建立 Python 环境与锁文件后确定；不得在此之前杜撰命令 |

后文保留的旧模板配置别名均按下表解释，不能另行替换为其他项目的值：

| 旧模板别名 | 本课题绑定值 |
|---|---|
| `<REPO>`、`<OWNER>`、`<DEFAULT_BRANCH>` | `Premise-Pinned-Response-Sets`、`EloiseJulia`、`main` |
| `<REPO_PATH>`、`<WORKTREE_ROOT>` | 本机项目根目录、`<REPO_PATH>/.worktrees` |
| `<SPEC_DIR>`、`<PLAN_DIR>`、`<RESEARCH_DIR>`、`<REPORT_STORE>` | `docs/specs/`、`docs/plans/`、`docs/research/`、本地 `artifacts/` |
| `<AGENT_CLI>`、`<MODEL>`、`<COMPUTE>` | GitHub Copilot、本次任务锁定的快照模型、本地 Windows 环境 |
| `<PROJECT_BOARD>`、`<TMUX_SESSION>`、`<COMMIT_TRAILER>` | 无、无、按当前 Git 身份生成（不伪造署名） |
| `<BUILD_CMD>`、`<RUN_CMD>`、`<TEST_CMD>` | 在 WP2 建立项目脚手架与锁文件后填入；在此之前该 gate 不可声称通过 |

### 0.1 不可变的实验协议

- **数据与任务**：仅从 ChaosNLI 的约 3,100 条中抽取 SNLI 150 条、MNLI 150 条；SummEval-Relevance 150 条。NLI 的人工分布必须来自 ChaosNLI，禁止从 SNLI/MNLI 原始集重抽替代。
- **比较路径**：强制单选 F（20 次重采样）、自报 response set S（20 次）和前提钉住 P。P 的自曝阶段重复 3 次；第二阶段每次只钉住一个前提维度。全网格仅可作为每任务 20 条的子集消融。
- **不能改变的测量方向**：危险象限是 $H_{seed} \leq 0.5$ bit 且 $H_{ctx} > 0$，不是高种子熵；人类阈值 $\pi$ 必须扫描 0.05--0.25（步长 0.05），A 的阈值 $\tau$ 也必须全扫描。
- **失败不得伪造数据**：`parse_status` 只能为 `ok`、`malformed_json`、`missing_field`、`refused`、`timeout` 或 `provider_error`。非 `ok` 记录的解析字段必须为 null，禁止均值、众数或哨兵值填充。
- **调用可重现性**：缓存键必须覆盖渲染后提示、模型快照、温度、`top_p`、种子和响应格式；必须记录选项排列种子、原始全文、时间、token 计数、git SHA 与预注册标签。
- **合规**：`lguerdan/indeterminacy` 与 `lguerdan/doubly-robust-llm-judge` 仅以锁定 commit 的 submodule 引用，不复制未授权代码。转为公开或投稿前，必须重新完成许可证与作者授权审查。

### 0.2 研究资产地图

| 位置 | 用途 | 可进入主分支的证据 |
|---|---|---|
| `docs/plans/research-roadmap.md` | 全部工作包、依赖和门禁 | 工作包验收、风险与偏离处理 |
| `docs/specs/` | 每个实现或实验 slice 的目标、非目标、接口、验收 | 代码与配置变更的可追溯依据 |
| `docs/research/` | 上游离散化、数据许可、模型快照与文献核查 | 结论、来源链接、日期和 caveat |
| `docs/experiments/` | 预注册、偏离日志、运行清单、结果摘要 | git tag、输入清单、产物哈希、重建命令 |

> 没有偏离日志批准，§0.1 的实验参数不得由 agent 自行调整。

---

## 1. 研究定位与五条铁律

**以 PPRS 检验 rubric 歧义下的评分不确定性：Spec-Driven Research + Agent Execution + 独立审计 Gate。**

质量不是靠「用了多少 agent」堆出来的，而是靠**验证机制**守出来的。五条铁律（每条都是踩坑换来的）：

| # | 铁律 | 教训 |
|---|---|---|
| 1 | **验证可重建结果，不只看测试绿** | 三张图必须能由原始 Parquet、锁定配置和脚本重建；手工图或未记录参数不是结果 |
| 2 | **独立敌对审计 > 自审** | 审计者重点攻击解析失败填充、缓存键漏维度、错误危险象限和数据泄漏 |
| 3 | **并行只对独立切片** | 数据 schema、调用层、分析指标和图表共享契约；有依赖的切片必须串行 |
| 4 | **预注册冻结后不漂移** | 模型快照、阈值扫描、假设和主图改动必须进偏离日志，不能静默优化结果 |
| 5 | **诚实边界是交付物** | ChaosNLI 与 SummEval 的人类参照强度不同，且前提自曝构念尚未独立验证；报告必须分开陈述 |

外加一条贯穿铁律：**「标注边界 ≠ 修 bug」**——低风险且真超范围的可文档化为「已知边界」；但**会静默丢数据 / 破坏正确性**的（如身份维度缺失、窗口截断丢帧）**必须修**。

---

## 2. 三层文档体系（全部 git 追踪）

| 层 | 位置 | 作用 | 谁拥有 |
|---|---|---|---|
| **执行规范** | `AGENTS.md`（或本文件） | 定义 HOW：worktree 隔离 / PR 流程 / 分支命名 / commit 规范 / auto-merge 策略 / 看板更新 | 人（项目主人） |
| **设计规格** | `<SPEC_DIR>` | 每个 issue 一个 spec：Objective → Non-goals → Surface → Design → Acceptance Criteria → Slice Plan | 人 或 Agent（讨论后写） |
| **执行脚本** | `<PLAN_DIR>` | 每个 slice 一个 plan：架构图 + 数据流 + 分步骤 checklist + 测试步骤 + push 点 | Agent（执行中生成） |
| **调研报告**（可选） | `<RESEARCH_DIR>` | SOTA 调研 / 选型 / license 审查 | Research Agent |

**Spec 与 Plan 都可以由 Agent 写**，但必须**经你确认后 commit**。区别：
- **单 issue 交互模式**：讨论后 Agent 写 spec（人机协作，spec 质量取决于讨论深度）。
- **多 issue 非交互模式**：Agent 自主写 spec，所以 **issue body 质量决定 spec 质量**。

---

## 3. 全生命周期总览

```
① 调研(可选) → ② Issue 准备 → ③ 拆分+依赖分析 → ④ 每 slice 执行
                                                        ↓
        ⑦ 交付给你(不 merge) ← ⑥ 整体 PR-Audit ← ⑤ 独立敌对审计(每 slice)
                    ↓
        你决定 → mark ready → 交 owner review + merge
```

**不可跳过的 gate：**
- 每个 slice 完 → ④自检 + ⑤独立敌对审计
- 全部 slice 完 → ⑥整体 PR-Audit（build 真产物 + 全量测试 + diff 卫生）
- 交付前 → ⑦先发你，不 ready、不 merge

---

## 4. 角色总表

| 角色 | 何时用 | 位置 | 关键约束 |
|---|---|---|---|
| **你（人）** | 全程 | 本地 / 浏览器 | 唯一强制触发点；判断题的最终裁决者；merge 决定 |
| **Research Agent**（可选） | 技术路线/选型不明 | 独立 session，doc-only | 输出 research md，直接 commit `<DEFAULT_BRANCH>`；不写代码 |
| **Manager Agent** | 多 slice / 多 issue | 长驻 session（`<COMPUTE>`） | **先画依赖图**；只有它碰 git/topic；永不碰主 checkout、永不 merge 进主干 |
| **Sub-Agent（执行）** | 每个 slice | 独立 worktree + session | 只在自己 worktree；spec→plan→执行；自检 gate |
| **Audit Agent（独立敌对）** | 每 slice 完 + 整体 | **全新 session、无上下文** | 目标是挑毛病；不信任何既有结论；只报不修 |

**两种规模：**
- **单 issue（日常默认）**：不需要 Manager。你在 worktree 里起一个交互 session，讨论 → spec → plan → 执行 → review。
- **多 issue 并行（高级）**：才需要 Manager Agent 编排多个 Sub-Agent。

---

## 阶段 0 · 调研（可选，技术路线不明时）

**何时需要**：选模型 / 定算法路线 / 审 license / 比 SOTA。

**启动模板：**
```bash
<AGENT_CLI> --name research-<topic> --model <MODEL> \
  -i 'Research SOTA for <topic> (issue #<N>). Compare: <候选 A/B/C>.
For each: accuracy/benchmark, LICENSE (permissive vs restrictive), input/output
format, runtime cost, integration fit with our <现有框架>.
Read AGENTS.md §<相关章节> first.
Output <RESEARCH_DIR>/<date>-<topic>.md with a comparison TABLE + a clear
recommendation + rationale + honest caveats.
Commit directly to <DEFAULT_BRANCH> (doc-only). Trailer: <COMMIT_TRAILER>'
```

**关键**：让它输出**对比表 + 推荐 + 诚实 caveat**（尤其 license：可商用 vs 仅研究用途）。

**能做 / 不能做**：能搜文献/仓库/官方文档、比公开 benchmark、审 license、读本仓库理解集成约束；**不能**跑重型 benchmark（那要执行 agent）、不能保证结论绝对准（你最终判断）。

---

## 阶段 1 · Issue 准备

| 情况 | 做法 |
|---|---|
| 已有合适 open issue | 确认 body 够详细 |
| body 太简单 | 先补 body（acceptance criteria + 相关文件/模块 + Non-goals + parent epic 链接） |
| 全新工作 | 创建 issue，写清 body |

**「body 够详细」=**：① 说清做什么（acceptance criteria）② 提到相关文件/模块/现有模式 ③ parent epic 链接 ④ Non-goals（告诉 agent 什么不要动）。

> 单 issue 交互模式下 body 可以不完整（讨论时补）；**Manager 非交互模式下 body 必须完整**（没有讨论机会）。

**（可选）登记看板 `<PROJECT_BOARD>`**：设 Status=In progress，填 Agent 字段（谁在干、worktree 路径、session 引用），方便你随时知道谁在做什么。

---

## 阶段 2 · 拆分 + 依赖分析（最容易出错的一步）

**先画依赖图，再决定并行还是串行。**

```
对每个候选 slice 问：它读/写哪些文件、哪些模块、哪些数据结构？
  ├─ 两个 slice 改同一批文件 / 后者依赖前者产物  → 串行（依赖链）
  └─ 完全独立（不同文件、无产物依赖）           → 并行（独立切片）
```

- **依赖链**（如：建结构 → 扩展 → 改上游接口）：**串行**。硬并行会冲突，且跨切片的一致性 bug 更隐蔽。
- **独立切片**（如多个互不相关的 bug fix）：**并行**，各自独立 worktree；重型任务受资源上限约束（如一张 GPU 一个 agent）。

**产物**：Manager 写 spec + per-slice plan，标明每个 slice 的**依赖关系 + 并行/串行编排**，commit 到 topic 分支。

---

## 阶段 3 · 每个 Slice 执行

### 3.1 脚手架
```bash
git -C <REPO_PATH> worktree add <WORKTREE_ROOT>/<name> -b feature/<N>-<name> <DEFAULT_BRANCH>
cd <WORKTREE_ROOT>/<name>
git commit --allow-empty -m "bootstrap #<N>

<COMMIT_TRAILER>"                    # 空分支开不了 PR，先引导提交
git push -u origin feature/<N>-<name>
# 开 draft PR（用你的 PR 工具），base=<DEFAULT_BRANCH>，body 写 "WIP. Refs #<N>."
```
> **早开 draft PR** 拿 CI + owner 可见性；**但不 mark ready、不 merge**。

### 3.2 执行流程（spec → plan → code）
1. 贴**开场 prompt**（§使用方法 A）→ agent 读代码 + 问 ≤5 个澄清问题
2. 你答问 → agent 写 **spec** → 你确认
3. agent 写 **plan** → 你确认
4. agent 执行：写代码 → 跑测试 → 自检 → push（累积在 draft PR）

**你在关口把关**：spec 看 Acceptance Criteria + Non-goals + 拆分；plan 看是否覆盖验收 + 有测试步骤 + 有 push 点。**判断题（选哪个方案、要不要扩范围）由你拍板，不让 agent 闷头猜。**

### 3.3 自检 gate（agent mark ready 之前必须自答）
- 目标产物真的能跑（不只是 import / 单测）？
- 幂等？重跑收敛？
- **身份维度完整**（主键/标识没漏维度 → 避免不同配置静默撞车）？
- 无依赖 / 空输入优雅降级？
- diff 只动该动的，无残留 debug / 无误删？

---

## 阶段 4 · 独立敌对审计（质量皇冠，每 slice 完做）

**必须是全新 session、无上下文、抱着「我一定要挑出毛病」的心态**——写代码的 agent 审自己有偏见。

审计 prompt（§使用方法 D）核心：
- 「你没写这份代码，把 PR 描述和一切既有结论当**不可信**，从源码重新验证」
- **先读代码找逻辑 bug**（身份维度缺失 / 静默丢行 / 坐标/数值缩放 / 注入 / 多步写原子性 / 旁路校验），再跑验证
- **验证真实产物**（build + run，不只单测）
- **独立归因测试失败**（clean `<DEFAULT_BRANCH>` 对比复现，禁止「猜 pre-existing」）
- 输出 **ranked findings**（BLOCKER/MAJOR/MINOR/UNVERIFIED）+ 明确 verdict；**只报不修**

**审计回来后分诊：**
- 我们代码 + 修法清楚 → 修
- 共享 infra / owner 说过别动 → **不擅改，文档 + follow-up issue，交 owner**
- 会静默丢数据 / 破坏正确性 → **必须修**（哪怕它自称「边界」）

---

## 阶段 5 · 整体 PR-Audit（全部 slice 完，合并前一次总检）

| 面 | 查什么 |
|---|---|
| **A 真实产物** | `<BUILD_CMD>` + `<RUN_CMD>` 跑通；其它产物消费者没被连累 |
| **B 幂等/共存** | 重跑 0 新副作用；多配置共存不撞；超限报错不静默丢；`--force`/重置干净 |
| **C 结构/接口** | 统一视图/接口单值不 fan-out；约束真强制；下游消费者不被破坏 |
| **D 正确性** | 数值/坐标 round-trip；无依赖优雅 skip；空输入不崩 |
| **E 全量回归** | 跑**整个**测试套（不只子集）；每个失败 clean-main 独立归因 |
| **F diff 卫生** | 逐行看配置/依赖文件，防「误删」；无 throwaway/debug 残留；worktree 干净 |
| **G review 闭环** | 所有 review thread 回复 + 真修（不只回复）；lint |

**产出**：PASS/FAIL 表 + ranked findings。确认的 bug 修，判断题标注交你/owner。

---

## 阶段 6 · 交付（先发你，不 merge）

- **先发你**：报告 / `git diff <DEFAULT_BRANCH>...feature/<N>` / PASS-FAIL 表。**不 mark ready、不 merge。**
- 你审完 → 才 mark PR ready → 交 owner review + merge。
- 共享 infra 改动在 PR body/commit 里**单独标注 "needs your sign-off"**。
- **（可选）图文报告**：结果 + 可视化 + 指标 + **诚实的精度验证**。
  - 别 overclaim：无 ground truth 时说清「是合理性/一致性/稳定性验证，不是误差 vs 真值」；要真误差就用**带 GT 的标定数据集**，并写明域差距。
  - 重型产物（图/大文件）放 `<REPORT_STORE>`（git 外），只把摘要发 PR。

---

## 7. 贯穿原则 · Gate · 陷阱速查

| 类别 | 要点 |
|---|---|
| **只读主 checkout** | agent 永不改 `<REPO_PATH>` 主 checkout；只 `git worktree add` / 只读 inspect（`git log/status/diff`） |
| **禁止在主 checkout 上 test-checkout** | 临时 checkout 某 commit 也不行（会留 detached HEAD）；要看某 commit 用临时 worktree |
| **PR-first 但不 merge** | 早开 draft 拿 CI/可见性；ready/merge 是人的动作 |
| **commit trailer** | 每个 commit 带 `<COMMIT_TRAILER>` |
| **空分支陷阱** | 0-commit 开不了 PR → 先 `git commit --allow-empty` 引导提交 |
| **删 worktree 陷阱** | 先 `cd <REPO_PATH>` 再 `git worktree remove`，否则后续 shell 找不到 cwd 报 ENOENT |
| **身份维度陷阱** | 主键/identity 要包含「所有影响输出的维度」（strategy/size/config），否则静默撞车 |
| **验证真实产物** | 测试绿 ≠ 产物能用；build + 跑真产物 |
| **别猜 pre-existing** | 任何「预先存在的失败」结论必须 clean-main 复现坐实 |
| **何时停** | 一道彻底审计 0 新问题 → 交付；别无限自证 |
| **squash 进 topic 的隐患** | slice squash-merge 进 topic 会压平历史，topic→main 可能报 dirty；优先 `--merge` 或 squash 后立即 `git merge --no-ff origin/<DEFAULT_BRANCH>` 补桥 |

---

## 8. 分支命名约定

| 类型 | 格式 | 示例 |
|---|---|---|
| 新功能 | `feature/<short-name>` | `feature/123-add-cache` |
| Bug fix | `fix/<short-name>` | `fix/456-null-deref` |
| 重构 | `refactor/<short-name>` | `refactor/config-loader` |
| 实验 | `experiment/<short-name>` | `experiment/new-algo` |
| 多 slice 伞状 | `topic/<name>` | `topic/123-search-rework` |
| sub-agent slice | `slice/<topic>-S<N>` | `slice/123-S1-index` |

**Topic 模式**（多 sub-agent 并行）：
```
topic/xxx（伞状，Manager 维护）
  ├── slice/xxx-S1（Sub-Agent 1，auto-merge 进 topic）
  ├── slice/xxx-S2（Sub-Agent 2，auto-merge 进 topic）
  └── topic → <DEFAULT_BRANCH>（人工 approve 一次）
```

**auto-merge 策略**：slice → topic 可由 Manager 验证后 auto-merge；topic → 主干**永远需要人 approve**，即使 CI 全绿。

---

## 9. Agent 运维（监控 + 故障处理）

**监控**：
- 长驻 session 直接看（`tmux attach-session -t <TMUX_SESSION>`）
- 若 CLI 支持远程可见性，用浏览器监控 session（SSH 断开不影响）
- 看 PR 状态（draft = 工作中；non-draft = 自检通过等 review）
- 看看板 Status

**卡住 / 需要回应**：Agent 会在 blocking question 前 stop（不瞎猜）。用 `tmux send-keys` 或远程 session 页面回应。

**崩溃恢复**：找到 session ID → 用 CLI 的 resume 能力从断点继续，已 push 的 commits 不重做。

**完成后清理**（避免 worktree 堆积）：
```bash
cd <REPO_PATH>                                          # 先离开 worktree！
git worktree remove --force <WORKTREE_ROOT>/<name>
git branch -D feature/<N>-<name>                        # PR 已 merge 时
# 关掉对应长驻 pane
```

---

## 10. 明确不存在的东西（避免误解）

| 不存在 | 说明 |
|---|---|
| Goal → Spec 全自动 | issue 仍需人判断业务价值后创建 |
| 独立「Planner Agent」角色 | Manager 兼任规划职能 |
| 持久化向量记忆 / 知识图谱 | 仅有文件式 handoff 记忆（`docs/<date>-handoff.md`，git 追踪，session 间接力）|
| Agent 自主 approve 自己的 PR 进主干 | 平台限制 + 本规范明确禁止 |

---

## 11. 使用方法 · Prompt 模板全集

### A. Sub-Agent 开场 prompt（单 slice 执行）
```
You are working on issue #<N> (slice <k>), branch feature/<N>-<name>, draft PR
#<PR>. Full flow: read context, ask ≤5 questions, write a SHORT spec, wait for
my confirm, write a plan, wait for my confirm, THEN execute.

Read ALL before asking:
- issue #<N> (+ parent epic)
- AGENTS.md §<相关章节>
- <相关现有代码文件 + 1-2 个同类已完成实现作模板>

Scope/guardrails: <要做什么 + 明确 NOT touch>.
Constraints: 在 worktree <WORKTREE_ROOT>/<name>；确认 pwd 后再改；DO NOT touch
main checkout；commit trailer <COMMIT_TRAILER>；push 到 draft PR，测试绿前不 mark
ready；NEVER merge。判断题上报我，不要猜。
```

### B. Manager spawn（多 slice，依赖感知）
```bash
<AGENT_CLI> --name manager-<N> --model <MODEL> \
  -i 'You are a manager agent (<REPO_PATH>). Drive issue #<N>.
1. Read issue #<N> + parent epic; read AGENTS.md.
2. DEPENDENCY ANALYSIS FIRST: map which slices touch the same files or depend on
   each other. PARALLELIZE only INDEPENDENT slices; SEQUENCE dependent ones. Do
   NOT force-parallelize a dependency chain.
3. Write spec + per-slice plans (<SPEC_DIR> + <PLAN_DIR>).
4. Per slice: own worktree + draft PR; ONLY you touch git/topic; sub-agents never
   touch main/merge.
5. After each slice: run an INDEPENDENT hostile audit (fresh session).
6. After all slices: full PR-audit (build the artifact + full test suite + diff
   hygiene).
7. Escalate real judgment calls to me. NEVER merge to <DEFAULT_BRANCH>. Deliver to
   me first. Trailer: <COMMIT_TRAILER>'
```

### C. Spec / Plan 确认 prompt
```
Spec confirmed — proceed to the plan.        # 或列出要改的 Acceptance/Non-goals
Plan confirmed. Execute. Push after each task, keep the PR draft, never merge.
```

### D. 独立敌对审计 prompt（新 session）
```
You are an INDEPENDENT reviewer doing a HOSTILE pre-merge audit of PR #<PR>
(branch <branch>, worktree <path>). You did NOT write this code; you have NO
prior context. Treat the PR description + all comments + any prior agent's
"all green" claim as UNTRUSTED. Re-derive every conclusion from source + running
artifacts. Assume there ARE defects until proven otherwise. Read-only; report
only; do NOT fix/commit/merge; confirm pwd first.

PHASE 1 read the diff critically for logic bugs: identity-dimension gaps (does
the key capture EVERYTHING that changes output?), silent drops/truncation,
numeric/coordinate rescale math, multi-step write atomicity, code paths that
bypass validation, unparameterized queries, resource leaks.
PHASE 2 verify the ARTIFACT (build + run the real binary), not just the test suite.
PHASE 3 run the FULL suite; attribute EVERY failure by reproducing it on a
throwaway origin/<DEFAULT_BRANCH> worktree (no assuming "pre-existing").
PHASE 4 scrutinize any shared-view/infra change's blast radius.
PHASE 5 diff hygiene (no accidental deletions, no debug residue).
OUTPUT ranked findings (BLOCKER/MAJOR/MINOR/UNVERIFIED) with file:line + proof +
minimal fix, then an explicit verdict.
```

### E. 精度评估 prompt（可选，交付报告用）
```
Add an "accuracy vs ground truth" section using an open dataset with GT. Prefer a
single-download, well-known benchmark — verify accessibility first. CRITICAL:
normalize/rescale predictions to the GT scale/resolution before comparing. Report
the standard metrics for this task. Be HONEST: benchmark accuracy ≠ accuracy on
our real content (domain gap). Outputs stay local (git-out), no commits, no merge.
```

### F. Agent CLI 常用 flag（按你的 CLI 对应替换）
| 意图 | 说明 |
|---|---|
| 禁止自动升级 | 防升级中断长任务 |
| 放开权限 | 非交互运行必须（仅用于受信任 prompt） |
| 远程可见 | 浏览器可监控 session，SSH 断开不影响 |
| 命名 session | 标签在 session 列表 / 看板可见 |
| 选模型 / 高强度 | 复杂任务用最强长上下文模型 + 高 effort |

---

## 12. 一页 Checklist（每个 issue 跑一遍）

```
调研(可选)
  □ 对比表 + 推荐 + license/可商用性 + 诚实 caveat

Issue 准备
  □ body 够详细(验收/文件/Non-goals/epic)  □ (可选)登记看板

拆分
  □ 画了依赖图  □ 独立→并行, 依赖→串行(没硬并行一条链)

每 slice 执行
  □ worktree + draft PR(不 ready)  □ spec 你确认  □ plan 你确认
  □ 自检: 真产物能跑 / 幂等 / 身份维度全 / 优雅降级 / diff 干净

独立敌对审计(每 slice)
  □ 新 session 无上下文  □ 先读代码找逻辑 bug  □ 验真产物  □ 失败 clean-main 归因
  □ ranked findings + verdict

整体 PR-Audit
  □ A 真产物 build+run  □ B 幂等/共存  □ C 结构/接口  □ D 正确性
  □ E 全量测试+归因  □ F diff 卫生  □ G review 闭环

交付
  □ 先发你(不 merge)  □ 共享 infra 标注 sign-off  □ (可选)图文+精度报告
  □ 你确认 → mark ready → 交 owner merge

铁律自检
  □ 验证了真实产物(不只测试)  □ 上了独立敌对审计  □ 并行只对独立切片
  □ 共享 infra 交 owner  □ 该修的修了(没拿"边界"糊弄)  □ 知道何时停
```

---

> **一句话收尾**：这套流程的价值不在「用了多少 agent」，而在**每个交付物都过了「独立敌对审计 + 验证真实产物」两道 gate，且每一处未验证/有意为之的边界都写清楚了**。换新项目时先做一次 §0 适配，之后照 §12 checklist 跑，任何 issue 的质量都可复现。
