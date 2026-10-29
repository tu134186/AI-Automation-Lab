# 中文报告中心
不需要 API 账户或独立网站。进入 GitHub Actions 任务摘要即可查看中文报告，底部提供下载入口。
每次任务导出 report.json、report.md、report.html、tests.log 和本次 Commit 对应的完整源码 ZIP。
HTML 无脚本、无外部资源，支持手机及系统深色模式；需要从产物下载后打开，GitHub 不直接托管此 HTML。
状态来自 unittest 实际结果及源码基础检查。错误、断言失败、失败的 subTest、跳过、预期失败均分别记录；空报告和跳过不会宣称全部通过。
修改记录取自本次 git show；任务及 Commit 链接取自 GitHub 运行上下文。页面中的下载入口指向任务页，任务摘要末尾另有真实产物链接。
原 lab_report.py CLI 和 JSON/Markdown/HTML 格式保留兼容。
运行：python3 scripts/run_report.py。退出码 0 表示所有检查通过，1 表示失败、跳过或无测试。
本分支源码变化触发一次 Linux 检查，同分支新任务自动取消旧任务；无需 iOS 云编译。
本阶段不包含离开对话后的通用 AI 自动修复。
