# RB-04：磁盘满

> **场景**：写入失败、健康检查报错
> **严重度**：P1
> **首响 SLA**：1 h

## 症状

- 健康检查失败：`No space left on device`
- Sentry 报 `OSError: [Errno 28]`
- 新用户注册失败（无法写 DB）

## 排查

```bash
# 1. 看磁盘
df -h
# 关注 Use% > 80%

# 2. 找大文件
du -sh /* | sort -h | tail -10

# 3. 看 Docker volumes
docker system df
docker volume ls
```

## 缓解

### 快速清理（10min）
```bash
# 清系统日志
journalctl --vacuum-time=3d
# 清 pip 缓存
pip cache purge
# 清 npm 缓存
npm cache clean --force
# 清旧 Docker 镜像
docker image prune -a --filter "until=72h"
# 清旧备份（保留最近 7 天）
find /backups -mtime +7 -delete
```

### 扩大磁盘（如果 Railway）
```bash
# 通过 Railway UI：Settings → Volumes → Resize
# 或 CLI
railway volume extend --size 5GB
```

### 长期方案
- 日志自动清理：logrotate / Docker log driver
- 监控提前预警：磁盘 > 70% 就告警
- 数据库迁移到云（Postgres on Railway / Supabase）

## 验证

```bash
df -h
# Use% < 70%
curl /api/health
# 200 OK
```

## 关联

- 监控：A-06、A-07
- 预防：logrotate 配置
