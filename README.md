# AI Automation Lab

## 手机查看入口

[打开报告中心任务列表](https://github.com/tu134186/AI-Automation-Lab/actions?query=branch%3Afeature%2Freport-center-20261029)

这是固定入口，不需要保存每次 Run ID。打开列表中最新的 Automation Lab Check 任务，查看摘要中的中文报告。
摘要末尾提供报告、日志和对应源码 ZIP 的下载链接；列表中的任务状态以 GitHub 显示为准。
HTML 为离线文件，需要下载后打开；GitHub 任务摘要可以直接在手机浏览器查看。

## 当前能力

连续生成报告不会立即挤掉较早的未解决失败：待处理和结果对比覆盖最多 100 次历史运行，列表保持 10 条。

- 优先显示待处理失败／等待任务，恢复通过的旧失败不再挂在清单中。
- 直达失败 Job 日志，导出独立 diagnosis.md／diagnosis.json 诊断清单。

- 实际测试结果及失败详情；保留旧 JSON、Markdown、HTML 导出接口。
- 扫描本仓库最多 100 次云端运行，页面展示最近 10 次，失败步骤及有效产物入口。
- 同工作流、同分支在最多 100 次历史扫描中的最近有效结果对比：新增失败、恢复通过、持续失败、持续通过。
- 有效历史结果的通过率；取消、跳过、等待和未知结论不进入分母。
- 独立测试分支，不修改主分支，无需额外 AI API 费用。

没有匹配的历史记录时显示暂无可比较记录。恢复通过只表示工作流结果恢复，不能证明某个具体产品 BUG 已修好。
数据为每次任务执行时的快照；当前进行中的报告任务不提前计为通过。

运行：`python3 scripts/run_report.py`。详细说明见 [报告中心文档](docs/report-center.md)。

---


隔离的自动开发测试仓库。当前示例：任务结果汇总器，使用 Python 3 标准库。

```sh
python3 lab_report.py examples/tasks.json
python3 -m unittest discover -s tests -v
python3 scripts/self_check.py
```

输入为 JSON 数组，每项包含唯一的 name 和 status（success/failure/running）。输出任务计数和 all_passed。
退出码：0 全部成功；1 存在失败、运行中或无任务；2 输入无效或无法读取。

开发在 setup/ai-automation-foundation 分支，main 保留。Actions 仅手动或相关 PR 变更触发，并取消同分支重复运行。云端执行是否成功以实际 Run 结果为准。

## Markdown 报告导出

```sh
python3 lab_report.py examples/tasks.json --markdown report.md
```

标准输出仍为原有 JSON，同时将汇总与任务表格写入 UTF-8 Markdown 文件。父目录须已存在；已有报告文件会被替换。无效输入不会覆盖报告；禁止输出到输入文件。导出失败返回 2，任务状态退出码仍保持原有规则。

## HTML 报告导出

```sh
python3 lab_report.py examples/tasks.json --html report.html
# 同时导出两种报告，标准输出仍为 JSON
python3 lab_report.py examples/tasks.json --markdown report.md --html report.html
```

HTML 为独立 UTF-8 文件，包含统计和任务表格，支持手机宽度，无脚本或外部资源；任务名称自动转义。可下载后用浏览器打开。

输出目录须已存在，已有同名报告会被替换。输入与输出、两种输出之间不得指向同一文件（含符号链接、硬链接）。无效输入不会覆盖报告；导出错误返回 2。双格式导出依次写入，若后一个文件写入失败，前一个可能已生成，不保证跨文件原子写入。任务成功、失败、进行中以及空记录的退出码保持不变。
