"""命令行：训练评分卡并输出评估指标"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal  # noqa: E402
from app.ml.training import run_training  # noqa: E402

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else None
    db = SessionLocal()
    try:
        result = run_training(n_samples=n, db=db, trained_by="cli")
    finally:
        db.close()

    print("=" * 50)
    print(f"模型版本      : {result['version']}")
    print(f"样本量        : {result['nSamples']}（违约率 {result['defaultRate'] * 100:.2f}%）")
    print(f"入模特征      : {result['nFeatures']} 个 → {result['featureNames']}")
    print("-" * 50)
    print(f"AUC           : {result['auc']:.4f}")
    print(f"KS            : {result['ks']:.4f}")
    print(f"召回率        : {result['recall']:.4f}")
    print(f"精确率        : {result['precision']:.4f}")
    print(f"F1            : {result['f1']:.4f}")
    print(f"准确率        : {result['accuracy']:.4f}")
    print(f"5折CV AUC     : {[round(s, 4) for s in result['cvScores']]}")
    print(f"PSI           : {result['psi']}")
    print(f"模型文件      : {result['artifactPath']}")
    print("=" * 50)
