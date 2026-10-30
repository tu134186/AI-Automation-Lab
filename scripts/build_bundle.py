"""Create and verify one offline delivery ZIP from the validated report folder."""
import argparse
import hashlib
from pathlib import Path
import stat
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.validate_delivery import verify as verify_delivery

def package_name(sha):
    import re
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("无效 Commit")
    return f"AI-Automation-Lab-{sha[:7]}-complete.zip"

def expected_names(sha):
    package_name(sha)
    return {"report.json","report.md","report.html","tests.log","history.json","history.md",
            "diagnosis.json","diagnosis.md","delivery.md","manifest.json","SHA256SUMS.txt",
            f"AI-Automation-Lab-{sha[:7]}-source.zip"}

def verify_bundle(archive_path, sha, run_id):
    archive_path = Path(archive_path)
    if archive_path.name != package_name(sha) or archive_path.is_symlink() or archive_path.stat().st_size > 10*1024*1024:
        raise ValueError("无效完整包")
    checksum = archive_path.with_suffix(".zip.sha256")
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    if checksum.is_symlink() or checksum.read_text() != f"{digest}  {archive_path.name}\n":
        raise ValueError("完整包 SHA-256 不一致")
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != expected_names(sha):
            raise ValueError("完整包文件集合不一致")
        if sum(info.file_size for info in archive.infolist()) > 20*1024*1024:
            raise ValueError("解压总大小超出限制")
        for info in archive.infolist():
            if (info.file_size > 5*1024*1024 or info.is_dir()
                    or stat.S_ISLNK(info.external_attr >> 16)):
                raise ValueError("完整包包含无效文件")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in names:
                (root / name).write_bytes(archive.read(name))
            verify_delivery(root, sha, str(run_id))

def build_bundle(folder, output, sha, run_id):
    folder, output = Path(folder), Path(output)
    if folder.resolve() == output.resolve():
        raise ValueError("完整包不能写回报告目录")
    verify_delivery(folder, sha, str(run_id))
    output.mkdir(parents=True, exist_ok=True)
    target = output / package_name(sha)
    checksum = target.with_suffix(".zip.sha256")
    if target.is_symlink() or checksum.is_symlink():
        raise ValueError("输出不能是符号链接")
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(expected_names(sha)):
            info = zipfile.ZipInfo(name, date_time=(1980,1,1,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (folder / name).read_bytes())
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    checksum.write_text(f"{digest}  {target.name}\n", encoding="ascii")
    verify_bundle(target, sha, str(run_id))
    return target

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        target = build_bundle(args.input, args.output, args.commit, args.run_id)
        print(f"Complete delivery ZIP verified: {target.name}")
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, UnicodeError) as error:
        print("Complete ZIP failed: " + str(error), file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

