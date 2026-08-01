"""命令行：初始化数据库（建表 + 默认管理员 + 默认配置）"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.init_db import full_init  # noqa: E402

if __name__ == "__main__":
    full_init()
    print("✅ 数据库初始化完成（表 + 默认管理员 admin/admin123 + 默认配置）")
