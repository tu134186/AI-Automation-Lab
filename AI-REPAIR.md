# AI 无人值守修复
此流程实际调用官方 Codex Action，不使用预写修复模板。
在测试分支提交 ai_repair_demo 或 ai_automation 变化时触发。
生成、独立复测、提交分为三个 job；模型只获得读取仓库权限，提交 job 不执行模型生成代码。
校验后只有 ai_repair_demo/metrics.py 可被提交。测试不从模型产物导入。
失败停止，无无限重试；最多一次模型修复；生成 10 分钟、复测和提交各 3 分钟。
模型访问需要仓库 Actions Secret OPENAI_API_KEY。没有密钥时明确报告 BLOCKED_MISSING_OPENAI_API_KEY，不冒充成功。
配置入口：https://github.com/tu134186/AI-Automation-Lab/settings/secrets/actions/new
填写 Name=OPENAI_API_KEY，Secret=你的 OpenAI API 项目密钥；不要发到聊天或源码。
密钥配置后，对本分支此文档之外的上述监听目录提交变动即可启动，或在失败的 Actions 任务中 Re-run all jobs。
仅处理本演示目录的 Python 问题；尚未验证其他语言及生产项目。主分支不变。
