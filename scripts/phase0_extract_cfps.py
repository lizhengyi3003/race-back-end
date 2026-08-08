"""Phase 0: 解压 CFPS 各波家庭层面数据（famconf + famecon）到 data/raw/cfps/。

CFPS 每年压缩包内含 adult/child/famconf/famecon/comm 等 .dta，
本脚本仅提取家庭问卷（famconf）与家庭经济（famecon），避免解压巨大的 adult 文件。
支持 .zip（zipfile）与 .rar（7z 命令行，需系统安装 7z）。
输出：data/raw/cfps/cfps{年份}famconf*.dta + cfps{年份}famecon*.dta
"""

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFPS_DIR = ROOT / "data" / "数据集" / "CFPS"
OUT_DIR = ROOT / "data" / "raw" / "cfps"


def _is_stata_archive(name: str) -> bool:
    n = name.lower()
    return "stata" in n and (n.endswith(".zip") or n.endswith(".rar"))


def _extract_zip(zp: Path) -> int:
    count = 0
    with zipfile.ZipFile(zp) as zf:
        targets = [n for n in zf.namelist() if ("famconf" in n.lower() or "famecon" in n.lower()) and n.lower().endswith(".dta")]
        if not targets:
            print(f"[跳过] {zp.name}: 无 famconf/famecon 条目")
            return 0
        for name in targets:
            out_path = OUT_DIR / Path(name).name
            if out_path.exists():
                print(f"[已存在] {out_path.name}")
                continue
            with zf.open(name) as src, open(out_path, "wb") as dst:
                dst.write(src.read())
            count += 1
            print(f"[解压] {Path(name).name}")
    return count


def _extract_rar(zp: Path) -> int:
    """用 7z 提取 .rar 中的 famconf/famecon（7z 支持按通配符提取）。"""
    if not shutil.which("7z"):
        print(f"[错误] {zp.name}: .rar 需要 7z，但系统未安装")
        return 0
    result = subprocess.run(
        ["7z", "l", str(zp)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    names = [ln.split()[-1] for ln in result.stdout.splitlines() if ".dta" in ln]
    fam = [n for n in names if "famconf" in n.lower() or "famecon" in n.lower()]
    if not fam:
        print(f"[跳过] {zp.name}: 无 famconf/famecon 条目")
        return 0
    count = 0
    for name in fam:
        out_path = OUT_DIR / Path(name).name
        if out_path.exists():
            print(f"[已存在] {out_path.name}")
            continue
        subprocess.run(["7z", "e", str(zp), name, f"-o{OUT_DIR}", "-y"],
                       capture_output=True)
        if out_path.exists():
            count += 1
            print(f"[解压] {Path(name).name}")
    return count


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not CFPS_DIR.exists():
        print(f"[错误] CFPS 目录不存在: {CFPS_DIR}")
        sys.exit(1)

    archives = [p for p in CFPS_DIR.glob("*/*") if p.is_file() and _is_stata_archive(p.name)]
    archives.sort()
    if not archives:
        archives = [p for p in CFPS_DIR.glob("*") if p.is_file() and _is_stata_archive(p.name)]

    total = 0
    for ar in archives:
        try:
            if ar.name.lower().endswith(".zip"):
                total += _extract_zip(ar)
            else:
                total += _extract_rar(ar)
        except Exception as e:  # noqa: BLE001
            print(f"[错误] {ar}: {e}")

    print(f"\n完成：本次共解压 {total} 个家庭层面 .dta 到 {OUT_DIR}")


if __name__ == "__main__":
    main()
