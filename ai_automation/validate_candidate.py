"""Validate candidate files without executing model-generated code."""
import ast
from pathlib import Path

def validate(data):
    if not data or len(data) > 12000:
        raise ValueError("候选源码为空或超出 12KB")
    text = data.decode("utf-8")
    tree = ast.parse(text)
    if not any(isinstance(n, ast.FunctionDef) and n.name == "success_rate"
               for n in tree.body):
        raise ValueError("缺少 success_rate 函数")
    return text

if __name__ == "__main__":
    source = Path("candidate/metrics.py")
    if source.is_symlink() or not source.is_file():
        raise SystemExit("无效候选文件")
    target = Path("ai_repair_demo/metrics.py")
    text = validate(source.read_bytes())
    if text == target.read_text():
        raise SystemExit("AI 未产生修改")
    target.write_text(text, encoding="utf-8")
