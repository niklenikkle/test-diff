# 仓库级代码审核汇总报告

**项目**: {project_name}
**审核模式**: 仓库级代码审核
**审核时间**: {timestamp}
**结果目录**: {output_dir}
**涉及语言**: {languages}
**扫描文件数**: {file_count}
**扫描代码行数**: {line_count}

---

## 本次使用的审核依据

- **语言 / 框架参考**: {language_references}
- **额外安全参考**: {security_references}
- **额外性能参考**: {performance_references}
- **流程 / 输出规范参考**: {workflow_references}

---

## 一页概览

- **结论**: {conclusion}
- **是否建议当前状态合并 / 部署**: {merge_readiness}
- **一句话总结**: {executive_summary}
- **问题总数**: {total_issues_count}
- **高优先级问题数**: {high_count}
- **中优先级问题数**: {medium_count}
- **低优先级问题数**: {low_count}
- **有问题文件数**: {files_with_issues_count}
- **未发现问题文件数**: {files_without_issues_count}
- **最主要风险类型**: {top_risk_types}
- **建议优先处理文件**: {priority_files}

---

## 问题统计

### 按优先级统计

| 优先级 | 数量 |
|--------|------|
{priority_summary_table}

### 按风险类型统计

| 风险类型 | 数量 |
|----------|------|
{risk_type_summary_table}

### 按文件分布统计

| 文件 | 问题总数 | 高 | 中 | 低 | 主要风险 |
|------|----------|----|----|----|----------|
{file_issue_summary_table}

---

## 关键问题速览

{global_key_findings}

---

## 全部问题清单

| 序号 | 问题标题 | 文件 | 位置 | 风险类型 | 优先级 | 影响摘要 | 修复建议 |
|------|----------|------|------|----------|--------|----------|----------|
{issues_table}

---

## 文件报告索引

| 序号 | 源文件 | 问题数 | 文件判断 | 报告路径 |
|------|--------|--------|----------|----------|
{file_report_index}

---

## 审核边界与说明

- **上下文范围**: {context_scope}
- **语言 / 框架覆盖**: {language_coverage}
- **是否包含完整文件上下文**: {full_context}
- **边界说明**: {review_notes}
