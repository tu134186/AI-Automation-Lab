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

## 交付一致性验证
打包源码后、上传前执行 scripts/validate_delivery.py。
检查报告 Commit、重算本次测试统计、历史统计与待处理清单，逐字重建 Markdown 和 HTML 对照 JSON，检查源码 ZIP CRC 及 git archive 内嵌的完整 Commit。
通过后生成 delivery.md、manifest.json 和 SHA256SUMS.txt，记录每个文件的字节数与 SHA-256；再次独立校验全部文件和标识。
校验失败会使任务失败，摘要明确标注下载仅供排查，不把文件上传成功冒充交付验证成功。
离线复核：python3 scripts/validate_delivery.py reports --commit FULL_COMMIT --run-id RUN_ID --verify。
需要先解压完整源码 ZIP，然后用其中脚本指向报告文件夹；脚本仅使用 Python 标准库。
SHA-256 校验用于发现损坏或错包，不是数字签名；交付一致性通过也不表示历史任务没有未解决失败。

## 固定报告分支
报告任务只读；单独 publish_snapshot Job 在整个报告任务成功后，下载本次产物，复核文件集合、大小、SHA-256、测试状态、Commit 和 Run ID。
发布器确认开发分支仍指向本次 Commit，避免过时任务覆盖最新报告。只可写 reports-latest 分支；首次创建，后续非强制快进更新。
该分支保存原交付包全部 12 个文件（含源码 ZIP），另生成 README.md 和 snapshot.json 作为入口与来源说明。代码不执行下载包中的任何内容。
固定入口：https://github.com/tu134186/AI-Automation-Lab/blob/reports-latest/report.md
独立报告分支内容不依赖 Actions 30 天保留期；删除仓库、分支或文件后仍会丢失，不是外部备份。
该分支额外的 README.md 和 snapshot.json 不属于原交付清单；离线核验时使用原始 12 个交付文件。
最新任务失败、核验失败或发布失败时不会将其标为成功，固定入口仍可能是旧快照；查看来源 Commit、Run ID 及更新时间确认。
只在指定开发分支成功运行后发布，PR 和其他分支不会写报告快照。不合并 main、不部署网站、不自动调用 AI。

## 手机总览
reports-latest/README.md 是简短总览：本次已核验检查、历史待处理数量、扫描次数、北京时间、来源 Commit 和 Run ID。
展示前 5 项待处理及排查方向，其余通过诊断清单查看；名称和文本转义，任务链接只由数字 ID 构造。
明确区分上次保存的成功快照与当前工作流状态。GitHub 状态徽章可能缓存或未加载，以当前任务列表为准，不把旧快照冒充实时状态。
总览仅在本次整个核验任务成功后更新，不把失败报告发布为成功；无需另建网站或安装 App。

## 已暂停实验
report_policy.json 明确列出工作流路径、分支与暂停原因。当前仅对 AI 无人值守修复实验的指定测试分支进行暂停分类，原因是暂不开通付费 API。
这是报告中的处置分类，不更改 GitHub 原始结论，也不更改工作流开关；不会隐藏历史失败或把它计为通过。
待处理与已暂停分别展示；原始证据任务、失败结论和暂停原因在诊断 JSON／Markdown／HTML／手机总览中保留。历史失败数量及成功率仍包括原失败。
移除暂停条目后，该未解决失败重新进入待处理清单；其他分支、其他工作流不受规则影响。
history.json schema=5，包含已使用的 policy；交付核验还会比较源码 ZIP 内的 report_policy.json，防止分类策略与源码错配。
