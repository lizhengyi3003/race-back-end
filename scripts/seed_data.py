"""命令行：生成合成样本数据（CSV）"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ml.seed import generate_samples  # noqa: E402

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    df = generate_samples(n=n)
    out = Path(__file__).resolve().parent.parent / "data" / "samples" / "synthetic_samples.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"✅ 已生成 {len(df)} 条合成样本 → {out}")
    print(f"   违约样本占比：{df['default'].mean() * 100:.2f}%")
