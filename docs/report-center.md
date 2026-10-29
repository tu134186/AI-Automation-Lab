# 中文自动化报告中心

## 手机查看
固定入口：https://github.com/tu134186/AI-Automation-Lab/actions?query=branch%3Afeature%2Freport-center-20261029
打开最新 Automation Lab Check 任务，在摘要查看报告；末尾下载包包含 HTML、JSON、Markdown、测试日志和本次 Commit 的完整源码 ZIP。
HTML 无脚本、无外部资源，支持手机与深色模式；需要下载后打开，GitHub 不托管该 HTML 网页。
原 lab_report.py 的 CLI、JSON、Markdown、HTML 导出接口保持兼容。

## 本次检查
python3 scripts/run_report.py 实际执行 unittest 和源码基础检查。
记录成功、失败、异常、subTest 失败、跳过、预期失败和意外通过。无测试、失败或跳过均不宣称全部通过。
修改记录来自 git show；链接来自运行上下文。离线使用无需 GitHub 或 OpenAI 密钥。

## 历史与待处理
Actions 使用自带只读令牌扫描本仓库最多 100 次最近运行，排除当前运行。报告列表只显示其中最近 10 次，统计、对比和待处理清单覆盖整个已扫描范围。
按 workflow_id（缺失时用工作流路径）及分支分组；在扫描范围内比较最近有效结果。缺少身份时不跨任务合并。
有效结果为 success、failure、timed_out、startup_failure；其他结果不参与成功率或通过／失败对比。分母为空时显示暂无有效结果。
同工作流、同分支最近有效结果成功后，更旧失败退出待处理；取消、跳过或未完成不证明旧失败已恢复。
清单为空只表示有限扫描内未发现待处理，不代表所有历史正常。100 次之前的任务不在覆盖范围。
恢复通过仅表示工作流结论恢复，不能证明具体 App 问题已完成真机验证。

## 有界查询与证据
每次最多 1 次运行列表请求、3 次失败 Job 查询、5 次产物查询，网络请求超时 15 秒。失败详情优先分配给尚未解决的失败，不被重复的已恢复失败占满。
仅展示未过期产物；没有产物、读取失败及查询限额均明确说明。失败 Job 提供直达日志页，不复制原始日志。
排查方向依据失败步骤名，未确认根因。不会自动重试、修改历史任务、部署网站或调用付费 AI。
历史为每次任务执行时的快照；不是实时监控，也未创建定时任务。

## 导出文件
report.json、report.md、report.html：本次测试；
history.json、history.md：历史，schema=4，包含 scanned_count、scanned_runs、metrics、triage 和可见 runs（最多10条）；
diagnosis.json、diagnosis.md：独立待处理清单；
tests.log：实际测试输出；
AI-Automation-Lab-COMMIT-source.zip：当前 Commit 对应完整源码。

当前独立报告分支只在相关源码变化时触发 Linux 检查，同分支新任务取消旧任务。主分支不变，无需 OpenAI API。
