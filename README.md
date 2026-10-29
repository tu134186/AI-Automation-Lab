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
