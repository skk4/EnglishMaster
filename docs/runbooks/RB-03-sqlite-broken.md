# RB-03：SQLite 损坏

> **场景**：用户登录/进度/对话历史 500
> **严重度**：P0（数据丢失风险）
> **首响 SLA**：30 min
> **解决 SLA**：4 h

## 症状

- 用户注册/登录 500
- 错误日志含 `database is locked` / `disk I/O error` / `database disk image is malformed`
- Sentry 报 SQLite 异常

## 排查

### 1. SSH 到生产
```bash
railway shell
# 或
ssh user@server
```

### 2. 立即停止写入
```bash
# Railway 会自动重启，但先停避免新数据覆盖损坏文件
# 找 process
ps aux | grep uvicorn
kill -STOP <pid>  # 暂停但不杀，等下一步
```

### 3. 完整性检查
```bash
sqlite3 /app/database/app.db "PRAGMA integrity_check;"
# 期望：ok
# 如果报 "database disk image is malformed" → 损坏
```

### 4. 看磁盘
```bash
df -h
ls -lh /app/database/
# 看是否有 .db-wal / .db-shm 残留
```

## 恢复

### 场景 A：轻度损坏（integrity_check 报 non-ok 但能读）
```bash
# 尝试导出
sqlite3 /app/database/app.db ".dump" > /tmp/dump.sql
# 重建
rm /app/database/app.db
sqlite3 /app/database/app.db < /tmp/dump.sql
# 验证
sqlite3 /app/database/app.db "PRAGMA integrity_check;"
# 期望：ok
```

### 场景 B：严重损坏（无法打开）
```bash
# 1. 拉最近备份
aws s3 cp s3://englishmaster-backups/sqlite/app-2026-06-01.db \
  /app/database/app.db

# 2. 重启服务（Railway 自动）
curl /api/health

# 3. 通知用户"系统维护中，您的最近数据可能丢失"
```

### 场景 C：磁盘满
```bash
# 找大文件
du -sh /app/* | sort -h | tail -10
# 清 log
journalctl --vacuum-time=1d
# 清 pip 缓存
pip cache purge
```

## 验证

```bash
# 1. 完整性
sqlite3 /app/database/app.db "PRAGMA integrity_check;"
# 2. 关键表行数
sqlite3 /app/database/app.db "SELECT 'users', COUNT(*) FROM users UNION ALL SELECT 'quiz_records', COUNT(*) FROM quiz_records;"
# 3. 试登录一个用户
curl -X POST /api/auth/login -d '{"username":"alice","password":"pw1234"}'
```

## 复盘必做

- 根因（硬盘？Bug？人为？）
- 备份是否最新
- RPO 影响（丢了多久数据）

## 关联

- 监控：A-06（磁盘 80%）
- 备份脚本：`scripts/backup/sqlite.sh`
- 演练：每季度一次
