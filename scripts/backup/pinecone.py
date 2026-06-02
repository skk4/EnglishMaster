#!/usr/bin/env python3
"""
Pinecone 索引元数据备份（每周）

保存 ID 列表和 metadata 索引（不是 vector 本体，Pinecone 自带 3 副本）。
如果索引丢失，可用此 + raw_pages JSON 重跑 03_embed_and_upload.py 重建。
"""
import os
import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pinecone import Pinecone


def main():
    parser = argparse.ArgumentParser(description="Backup Pinecone index metadata")
    parser.add_argument("--output-dir", default="./backups/pinecone", help="本地输出目录")
    parser.add_argument("--upload-s3", action="store_true", help="上传到 S3")
    parser.add_argument("--s3-bucket", default="englishmaster-backups/pinecone")
    args = parser.parse_args()

    load_dotenv()

    api_key = os.getenv("PINECONE_API_KEY")
    host = os.getenv("PINECONE_HOST")
    index_name = os.getenv("PINECONE_INDEX_NAME", "xsjkndb01")
    if not api_key or not host:
        print("ERROR: PINECONE_API_KEY or PINECONE_HOST not set")
        sys.exit(1)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[backup] Connecting to Pinecone '{index_name}' at {host[:50]}...")
    pc = Pinecone(api_key=api_key)
    index = pc.Index(host=host)

    stats = index.describe_index_stats()
    print(f"[backup] Total vectors: {stats.total_vector_count}, dim: {stats.dimension}")

    # 拉所有 ID + metadata（分页）
    all_records = []
    batch_size = 1000
    pagination_token = None

    print("[backup] Fetching all vector IDs + metadata...")
    while True:
        kwargs = {"namespace": "", "limit": batch_size, "include_values": False, "include_metadata": True}
        if pagination_token:
            kwargs["pagination_token"] = pagination_token
        try:
            result = index.list_paginated(**kwargs)
        except AttributeError:
            # 旧版本 API
            ids = [v.id for v in index.list(**kwargs)]
            if not ids:
                break
            fetch_result = index.fetch(ids=ids)
            for vid, vec in fetch_result.vectors.items():
                all_records.append({"id": vid, "metadata": vec.metadata or {}})
            if len(ids) < batch_size:
                break
            continue

        vectors = result.vectors or []
        all_records.extend([{"id": v.id, "metadata": v.metadata or {}} for v in vectors])
        print(f"  Fetched {len(all_records)} so far...")

        if not result.pagination or not result.pagination.get("next"):
            break
        pagination_token = result.pagination["next"]

    # 保存
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    output_file = out_dir / f"pinecone-meta-{timestamp}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "index_name": index_name,
            "host": host,
            "backup_time": timestamp,
            "total_vectors": stats.total_vector_count,
            "dimension": stats.dimension,
            "records": all_records,
        }, f, ensure_ascii=False, indent=2)

    size_mb = output_file.stat().st_size / (1024 * 1024)
    print(f"[backup] Saved {len(all_records)} records to {output_file} ({size_mb:.1f} MB)")

    # 上传 S3
    if args.upload_s3:
        try:
            import boto3
            s3 = boto3.client("s3")
            s3.upload_file(
                str(output_file),
                args.s3_bucket,
                f"pinecone-meta-{timestamp}.json",
            )
            print(f"[backup] Uploaded to s3://{args.s3_bucket}/")
        except ImportError:
            print("[backup] WARN: boto3 not installed, skipping S3 upload")
        except Exception as e:
            print(f"[backup] ERROR uploading to S3: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
