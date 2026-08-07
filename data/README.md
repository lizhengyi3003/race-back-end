# data 目录说明

本目录存放数据库文件、模型文件与竞赛研究数据集。

## 研究数据集（data/数据集/）— 存放于 Cloudflare R2

`data/数据集/`（约 1.4GB：CFPS / CHFS / CMES 调查数据）**不进 git**，
已由 `.gitignore` 忽略。数据备份在 **Cloudflare R2**：

- **Bucket**: `race-datasets`
- **前缀**: `datasets/`（结构同本地 `data/数据集/` 目录）
- **S3 端点**: `https://d08d42f9b1e53cc1648cdc9c1eab5a0e.r2.cloudflarestorage.com`
- 访问密钥见团队密码本/记忆笔记（R2 Access Key）

### 恢复下载命令

```bash
# 方式一：rclone
rclone copy r2:race-datasets/datasets ./data/数据集/ -P

# 方式二：aws cli（配置 R2 S3 端点后）
aws s3 sync s3://race-datasets/datasets ./data/数据集/

# 方式三：boto3 脚本（参考仓库外工具 upload_r2.py 反向）
```

> 提示：国内网络直连 GitHub LFS 上传大文件会被限速/掐断（AWS S3 不可达），
> 故数据集改存 R2（Cloudflare，国内可连通）。不要在 git 里重新加入大文件。

## 其他

- `models/`、`samples/`、`*.db` 同样被 .gitignore 忽略（保留目录结构）。
- `raw/`：CMES/CHFS 关键字段解压文件（约 150MB，被 .gitignore 忽略），
  由 `scripts/build_proxy_dataset.py` 读取生成 `samples/proxy_samples.csv`。
  需要时可从 `data/数据集/` 的 zip 中重新解压（仅 master_hh + CMES 主表即可）。
- 数据管道（Phase 3）说明见 `scripts/DATA_PIPELINE.md`。
