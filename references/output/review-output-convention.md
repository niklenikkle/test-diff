# 审核结果落盘约定

本文件用于约束 `code-reviewer-optimized` 在正式差异审查和全量扫描模式下的审核结果落盘行为。目标是让每次需要落盘的审查都留下可复查、可分析、可对比的产物，而不是只在终端或聊天中输出结果。

## 1. 输出目录约定

### 正式差异审查

正式差异审查的结果必须在统一审核输出根目录下创建，默认根目录为 `C:/Users/<username>/AppData/Local/magico/code-review/`：

- `diff_review/`

并在其下创建本次审查输出目录：

- `diff_review/<output_name>/`

其中：

- `output_name` 必须统一命名为 `YYYYMMDD_rREV`；例如 `20260402_r5`
- 若同名目录已存在，则按 `YYYYMMDD_rREV_1`、`YYYYMMDD_rREV_2` 继续递增，避免覆盖历史结果
- **凡是目录名或报告文件名中包含日期，必须先通过运行时工具读取当前真实时间后再命名；不要根据模型记忆、上下文日期或历史目录名推断当前日期**
- 如果本次为 SVN 审核，提交级结果目录名中的 revision 和 author 必须来自本次实际审核目标，不得自行猜测

### 仓库级审查

仓库级审查的结果必须在统一审核输出根目录下创建，默认根目录为 `C:/Users/<username>/AppData/Local/magico/code-review/`：

- `repo_review/`

并在其下创建本次审查输出目录：

- `repo_review/<output_name>/`

其中：

- `output_name` 必须统一命名为 `YYYYMMDD_repo`
- 若同名目录已存在，则按 `YYYYMMDD_repo_1`、`YYYYMMDD_repo_2` 继续递增，避免覆盖历史结果
- **凡是目录名或报告文件名中包含日期，必须先通过运行时工具读取当前真实时间后再命名；不要根据模型记忆、上下文日期或历史目录名推断当前日期**

## 2. 最低产物要求

### 正式差异审查

每次进入正式差异审查至少必须产出：

- `diff_review/<output_name>/repo_result.json`
- `diff_review/<output_name>/commits_result/`

如果本次为 SVN 审核，则每笔提交必须落到：

- `diff_review/<output_name>/commits_result/<revision_number>_reviewer_<author>/`

且每笔提交目录下必须包含：

- `diff.json`：该提交的结构化 diff 信息
- `review_result.json`：该提交的结构化审查结果
- `report.md`：该提交的人类可读审查报告

要求：

- 所有正式差异审查产物都必须显式写入上述目录，不得散落在统一审核输出根目录之外的其他未说明路径；不要写回目标仓库目录、当前工作目录或临时目录
- 报告内容中必须显式记录本次使用的审核依据，至少包括：
  - 适用的语言 / 框架 reference
  - 额外使用的安全 reference（如有）
  - 额外使用的性能 reference（如有）
  - 使用的流程 / 输出规范 reference（如 `references/output/review-output-convention.md`、`references/workflows/svn-workflow.md`）
- 如果没有创建这些产物，或报告中没有体现本次使用的审核依据，则该次审查不算完成
- **当本次为 SVN 审核时，不再生成按文件拆分的 Markdown 报告**

### 仓库级审查

每次进入仓库级审查至少必须产出：

- `repo_review/<output_name>/repo_summary.txt`
- `repo_review/<output_name>/repo_result.json`
- `repo_review/<output_name>/review_report.md`
- `repo_review/<output_name>/review_output/`

其中：

- `review_output/` 下应尽量保留原仓库目录结构
- 单文件结果应写为：`review_output/<原路径>_review.json`
- 其字段组织应参考 `assets/per-file-review-template.json`，至少包含 `file_path`、`status_code`、`issues`、`report`
- 即使某文件未发现值得报告的问题，也必须生成对应结果，并明确写出：**未发现值得报告的高置信度问题**

## 3. 正式差异审查的 JSON 结果约定

正式差异审查中：

- `repo_result.json` 用于保存本次差异审查的全局汇总结果，字段组织应参考 `assets/repo-result-template.json`
- `review_result.json` 用于保存单笔提交的结构化审查结果，字段组织应参考 `assets/review-result-template.json`
- `diff.json` 用于保存单笔提交的结构化 diff 信息，字段组织应参考 `assets/diff-json-template.json`
- 生成 JSON 时必须严格沿用模板中的字段名与层级结构，不要自行改名、删字段，或额外再造一套平行结构
- 对于 SVN / 提交文件场景，`review_result.json` 必须使用 **commit 级** 结构：顶层包含 `revision`、`message`、`author`、`file_count`、`issue_count`、`review_failed_count`、`severity_count_dict`、`type_count_dict`、`file_review_result`；不得再输出 `project_path` + `files[]` 这一旧结构
- `file_review_result` 必须覆盖本次纳入正式审查的每个变更文件；即使某文件未发现值得报告的问题，也应保留该文件项，并将 `status_code` 设为 `0`
- `status_code` 语义必须固定：`0` 表示该文件未发现值得报告的高置信度问题，`1` 表示该文件存在正式问题；`review_failed_count` 表示 `status_code != 0` 的文件数，不表示审查执行异常数
- 正式差异审查生成 `review_result.json` 后，必须运行 `python scripts/validate-review-json.py <review_result.json>` 做结构校验；校验未通过时不得宣称审查完成

对于 `review_result.json` 中的问题项，约束如下：

- 问题必须可定位、可解释、可修复
- 对并发、资源、生命周期、契约变化、配置语义变化等问题，`description` 或 `evidence` 应尽量体现证据链，例如执行路径、共享对象、生命周期边界、返回语义变化、调用方影响范围等，而不是只给结论标签
- 若证据链已闭环，可按正式问题输出；若仍依赖额外前提或上下文假设，应明确写成风险提示，而不是伪装成已确定成立的缺陷
- 同一提交、同一文件下若多个现象共享同一直接根因、同一执行路径或同一边界失守，应优先合并成 1 条主问题，在 `description` / `evidence` 中展开影响，而不是拆成多个重复问题
- 若某个问题违反了项目内 `CLAUDE.md` 或其他明确项目规范中的规则，则相关结果中的自然语言字段必须显式写出违反的规范编号和标题，例如：`违反项目规范：2.1 UI组件规范`
- 不要为了追求格式完整而强行把低置信度上下文现象写成独立问题项；证据不足时应优先降低确定性措辞，而不是抬高优先级

对于 `repo_result.json` 中的 `llm_usage`，约束如下：

- 若本次审查流程已接入可审计的 usage 统计源，则必须填写真实数据；不要估算、补算或凭印象填写
- `repo_result.json` 默认参考 `assets/repo-result-template.json` 的完整 `summary` / `tokens` / `performance` 结构
- 若当前流程未接入 usage 统计，或拿不到可信的 request / token / duration 原始数据，则必须把整个 `llm_usage` 对象替换为“未采集”结构，不要用 `0` 冒充真实统计
- `llm_usage` 的“未采集”推荐写法为：
  - `"llm_usage": { "collected": false, "reason": "本次审查未接入统一 usage 统计链路" }`
- 不要在“未采集”场景里保留模板中的 `summary` / `tokens` / `performance` 0 值字段，避免与真实统计混淆

## 4. 差异审查 Markdown 报告职责

`report.md` 应当是对应提交的总览页，用于帮助用户快速判断总体风险、问题分布和建议动作。

`report.md` 至少必须包含：

- 一页概览：让用户快速理解本次审核是否建议当前状态合并 / 提交、问题总量和最高风险
- 本次使用的审核依据：明确列出本次实际读取并应用的 language / security / performance / workflow references
- 若报告中存在性能类正式问题，则此处必须显式列出 `references/issue-types/performance.md`；不得写成“未额外读取性能 reference”或其他等价表述
- 全部问题清单：以表格或分节列出所有值得报告的问题
- 审核边界说明：明确静态分析范围、上下文限制和未验证项

如果本次未发现值得报告的问题，`report.md` 也必须明确写出：

- **未发现值得报告的高置信度问题**

此外，Markdown 报告在组织问题时也应遵守：

- 优先列出主问题，不要把同一根因拆成多个并列一级问题
- 若存在派生影响，放入主问题的影响分析中，而不是重复列项
- 问题数量应反映真实独立缺陷数，而不是分析维度数

## 5. 仓库级审查单文件结果要求

仓库级审查必须：

- 为每个纳入审核范围的代码文件生成 1 个 JSON 结果
- 写入 `repo_review/<output_name>/review_output/` 下
- 目录结构尽量镜像源代码目录结构
- 单文件结果字段组织应参考 `assets/per-file-review-template.json`，至少包含 `file_path`、`status_code`、`issues`、`report`

例如：

- 源文件：`src/api/user.ts`
- 单文件结果：`repo_review/<output_name>/review_output/src/api/user.ts_review.json`

如果某文件未发现值得报告的问题，也必须生成对应结果，并明确写出：

- **未发现值得报告的高置信度问题**

## 6. 报告语言要求

所有正式审查写入磁盘的自然语言内容默认必须使用中文。

包括：

- 差异审查的 `report.md`
- 仓库级审查的 `review_report.md`
- 仓库级审查单文件 JSON 结果中的自然语言字段
- 聊天中的结果摘要

严重性相关术语应保持固定映射：

- Markdown 报告中的问题优先级使用：`高 / 中 / 低`
- `review_result.json` 的单问题 `severity` 使用：`高级 / 中级 / 低级`
- 聚合统计字典 `severity_count_dict` 使用：`高危 / 中危 / 低危`

允许保留代码标识符、类名、函数名、API 名称、错误码等英文原文，但自然语言部分必须写成中文。

如果输出为英文，则视为未满足报告产物要求，需要重新生成。

## 7. 聊天中的最终回复要求

完成审查后，在聊天或终端中：

- 只返回简要结论
- 返回统一审核输出根目录下的结果目录路径
- 返回统一审核输出根目录下的关键产物路径
- 必要时再补 1-3 个最关键问题

差异审查应至少返回：

- `diff_review/<output_name>/`
- `diff_review/<output_name>/repo_result.json`
- `diff_review/<output_name>/commits_result/<revision_number>_reviewer_<author>/report.md`
- `diff_review/<output_name>/commits_result/<revision_number>_reviewer_<author>/review_result.json`

仓库级审查应至少返回：

- `repo_review/<output_name>/`
- `repo_review/<output_name>/repo_summary.txt`
- `repo_review/<output_name>/repo_result.json`
- `repo_review/<output_name>/review_report.md`

不要把长篇完整报告直接放在聊天里替代文件产物。
