"""Read a pinned published ZIP from GitHub and verify its entire offline delivery."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import zipfile
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_bundle import package_name, verify_bundle

REPO = "tu134186/AI-Automation-Lab"
MAX_FILE = 10*1024*1024
MAX_RESPONSE = 16*1024*1024

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def get_file(get_json, snapshot, name):
    if not re.fullmatch(r"[0-9a-f]{40}", snapshot) or name not in {"complete-delivery.zip","complete-delivery.zip.sha256"}:
        raise ValueError("无效下载目标")
    metadata = get_json(f"contents/{name}?ref={snapshot}")
    size, blob = metadata.get("size"), metadata.get("sha")
    if metadata.get("type") != "file" or type(size) is not int or size <= 0 or size > MAX_FILE:
        raise ValueError("远端文件类型或大小无效")
    if not isinstance(blob, str) or not re.fullmatch(r"[0-9a-f]{40}", blob):
        raise ValueError("远端 Blob 标识无效")
    body = metadata
    if metadata.get("encoding") != "base64" or not metadata.get("content"):
        body = get_json(f"git/blobs/{blob}")
    if body.get("encoding") != "base64" or not isinstance(body.get("content"), str):
        raise ValueError("远端未返回有效文件内容")
    encoded = body["content"].replace("\n","").replace("\r","")
    if len(encoded) > MAX_RESPONSE:
        raise ValueError("远端内容超出限制")
    data = base64.b64decode(encoded, validate=True)
    identity = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if len(data) != size or identity != blob:
        raise ValueError("远端 Blob 内容与标识不一致")
    return data

def verify_published(read_file, source, snapshot, run_id):
    if not re.fullmatch(r"[0-9a-f]{40}", source) or not re.fullmatch(r"[0-9a-f]{40}", snapshot):
        raise ValueError("无效源码或归档 Commit")
    if not str(run_id).isdigit() or int(run_id) <= 0:
        raise ValueError("无效 Run ID")
    data = read_file("complete-delivery.zip")
    checksum = read_file("complete-delivery.zip.sha256")
    digest = hashlib.sha256(data).hexdigest()
    if checksum.decode("ascii") != f"{digest}  complete-delivery.zip\n":
        raise ValueError("远端完整包 SHA-256 不一致")
    with tempfile.TemporaryDirectory() as folder:
        archive = Path(folder) / package_name(source)
        archive.write_bytes(data)
        archive.with_suffix(".zip.sha256").write_text(f"{digest}  {archive.name}\n", encoding="ascii")
        verify_bundle(archive, source, str(run_id))
    return {"verified": True, "source_commit": source, "snapshot_commit": snapshot,
            "run_id": str(run_id), "bytes": len(data), "sha256": digest, "files": 12}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, default=ROOT/"verification")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    try:
        if os.environ.get("GITHUB_REPOSITORY") != REPO:
            raise ValueError("只允许回读指定测试仓库")
        opener = build_opener(NoRedirect())
        token = os.environ.get("GH_TOKEN", "")
        def get_json(endpoint):
            request = Request(f"https://api.github.com/repos/{REPO}/{endpoint}",
                              headers={"Accept":"application/vnd.github+json",
                                       "Authorization":"Bearer "+token,
                                       "X-GitHub-Api-Version":"2022-11-28"})
            with opener.open(request, timeout=15) as response:
                raw = response.read(MAX_RESPONSE+1)
            if len(raw) > MAX_RESPONSE:
                raise ValueError("远端响应超出限制")
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise ValueError("无效远端响应")
            return result
        result = verify_published(lambda name:get_file(get_json,args.snapshot,name),
                                  args.source,args.snapshot,args.run_id)
        text = ("# 发布后下载回读：PASS\n\n"
                f"- 源码 Commit：{args.source}\n- 报告归档 Commit：{args.snapshot}\n"
                f"- Run ID：{args.run_id}\n- 下载字节数：{result['bytes']}\n"
                f"- SHA-256：{result['sha256']}\n"
                "- 从 GitHub 按锁定归档读取，12 个内部文件及源码包验证通过。\n")
        print("Published download round-trip: PASS")
        status = 0
    except (HTTPError, URLError, OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        reason = f"HTTP {error.code}" if isinstance(error,HTTPError) else type(error).__name__
        result = {"verified":False,"source_commit":args.source,"snapshot_commit":args.snapshot,"error":reason}
        text = "# 发布后下载回读：FAIL\n\n"+reason+"。未确认远端下载包通过；请查看任务日志。\n"
        print("Published download round-trip failed: "+reason,file=sys.stderr)
        status = 1
    (args.output/"download-verification.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    (args.output/"download-verification.md").write_text(text,encoding="utf-8")
    return status

if __name__ == "__main__":
    raise SystemExit(main())

