# AI Automation Lab

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
