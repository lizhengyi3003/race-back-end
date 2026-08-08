#!/usr/bin/env python3
"""解码 cloudflared tunnel token，输出结构（secret 隐藏）。"""
import json, base64

tok = open("/etc/cloudflared/token").read().strip()
d = json.loads(base64.urlsafe_b64decode(tok + "=" * (-len(tok) % 4)))
print("keys:", list(d.keys()))
for k, v in d.items():
    if k.lower() in ("s", "secret"):
        print(k, "= ***hidden***")
    else:
        print(k, "=", v)

# 顺带写 credentials 文件（供本地 config 模式使用）
tunnel_id = d.get("t") or d.get("tunnel_id")
if tunnel_id and ("s" in d or "secret" in d):
    cred = {
        "AccountTag": d.get("a") or d.get("account"),
        "TunnelID": tunnel_id,
        "TunnelSecret": d.get("s") or d.get("secret"),
    }
    path = f"/etc/cloudflared/{tunnel_id}.json"
    with open(path, "w") as f:
        json.dump(cred, f)
    print(f"credentials 已写入: {path}")
else:
    print("未识别 token 结构，跳过写凭证")
