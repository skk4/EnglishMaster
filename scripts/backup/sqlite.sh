#!/bin/bash
# SQLite 每日备份脚本
# 调度：cron `0 3 * * * /opt/englishmaster/scripts/backup/sqlite.sh`
#
# 环境变量：
#   DB_PATH - SQLite 文件路径（默认 ./database/app.db）
#   BACKUP_DIR - 本地备份目录（默认 ./backups/sqlite）
#   S3_BUCKET - S3 桶名（默认 englishmaster-backups/sqlite）
#   AWS_REGION - AWS 区域（默认 us-east-1）
#   RETENTION_DAYS - 本地保留天数（默认 7）
#   S3_RETENTION_DAYS - S3 保留天数（默认 30）

set -euo pipefail

DB_PATH="${DB_PATH:-./database/app.db}"
BACKUP_DIR="${BACKUP_DIR:-./backups/sqlite}"
S3_BUCKET="${S3_BUCKET:-englishmaster-backups/sqlite}"
AWS_REGION="${AWS_REGION:-us-east-1}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
S3_RETENTION_DAYS="${S3_RETENTION_DAYS:-30}"

DATE=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="$BACKUP_DIR/app-${DATE}.db"

mkdir -p "$BACKUP_DIR"

echo "[backup] Starting at $(date -Iseconds)"
echo "[backup] Source: $DB_PATH"
echo "[backup] Target: $BACKUP_FILE"

# 1. SQLite 在线备份（不锁表）
if command -v sqlite3 &> /dev/null; then
    sqlite3 "$DB_PATH" ".timeout 30000" ".backup '$BACKUP_FILE'"
    echo "[backup] Local backup OK: $(ls -lh "$BACKUP_FILE" | awk '{print $5}')"
else
    # 退化：直接 cp（不推荐，可能不一致）
    echo "[backup] WARN: sqlite3 not installed, falling back to cp (not safe for active DB)"
    cp "$DB_PATH" "$BACKUP_FILE"
fi

# 2. 上传到 S3（如果配了 AWS CLI）
if command -v aws &> /dev/null && [ -n "${AWS_ACCESS_KEY_ID:-}" ]; then
    aws s3 cp "$BACKUP_FILE" "s3://$S3_BUCKET/" \
        --region "$AWS_REGION" \
        --storage-class STANDARD_IA
    echo "[backup] S3 upload OK"
else
    echo "[backup] WARN: AWS CLI not configured, skipping S3 upload"
fi

# 3. 清理本地老备份
find "$BACKUP_DIR" -name "app-*.db" -mtime +"$RETENTION_DAYS" -delete
echo "[backup] Local retention: $RETENTION_DAYS days"

# 4. 清理 S3 老备份
if command -v aws &> /dev/null && [ -n "${AWS_ACCESS_KEY_ID:-}" ]; then
    cutoff=$(date -d "$S3_RETENTION_DAYS days ago" -Iseconds 2>/dev/null || date -v -"${S3_RETENTION_DAYS}"d -Iseconds)
    aws s3api list-objects-v2 --bucket "${S3_BUCKET%%/*}" --region "$AWS_REGION" \
        --query "Contents[?LastModified<='${cutoff}Z'].Key" \
        --output text | xargs -I {} aws s3 rm "s3://$S3_BUCKET/{}" --region "$AWS_REGION"
    echo "[backup] S3 retention: $S3_RETENTION_DAYS days"
fi

# 5. 通知（如果配了 Slack）
if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
    curl -sS -X POST "$SLACK_WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"✅ SQLite backup OK at $DATE ($(ls -lh "$BACKUP_FILE" | awk '{print $5}'))\"}"
fi

echo "[backup] Done at $(date -Iseconds)"
