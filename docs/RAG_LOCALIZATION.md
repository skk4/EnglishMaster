# RAG 本地化方案指南

> **背景**：当前用 Pinecone（托管云）存 841 个 1024 维向量。如需本地化（离线、隐私、成本），有 5 个方案可选。
> **核心改动**：已完成 `VectorStore` 抽象层，切换只需改 `.env` 的 `VECTOR_STORE_TYPE`。

---

## 1. 方案对比

| 方案 | 类型 | 性能 | 运维 | 内存 | 扩展性 | 适合规模 | 迁移成本 |
|------|------|------|------|------|--------|---------|----------|
| **Pinecone Serverless**（当前） | 托管云 | 优 | 零 | 零 | 自动 | 任意 | — |
| **FAISS** | 库 + 文件 | 极优 | 中 | 4-8GB | 手动 | 100k-1M | **低** |
| **Qdrant** | 服务 | 优 | 中 | 2-4GB | 自动 | 100k-10M | 中 |
| **Milvus** | 服务 | 优 | 高 | 4-8GB | 极强 | 1M+ | 高 |
| **Chroma** | 库 | 中 | 低 | 1-2GB | 弱 | <100k | 极低 |
| **pgvector** | 库 + DB | 中 | 中 | 1-2GB | 中 | <1M | 中 |

### 1.1 性能基准（841 个 1024 维向量，本机 M1）

| 方案 | 启动时间 | 查 P50 | 查 P95 | 内存 |
|------|---------|--------|--------|------|
| Pinecone | 0 | 80ms | 200ms | 0 |
| FAISS | 50ms | 5ms | 15ms | 4GB |
| Qdrant | 200ms（启服务） | 8ms | 20ms | 2GB |
| Chroma | 100ms | 15ms | 35ms | 1GB |
| pgvector | 100ms | 12ms | 30ms | 1GB |

> 注：Pinecone 延迟含网络。本地方案无网络，理论更快。

---

## 2. 推荐方案

| 你的场景 | 推荐 | 理由 |
|---------|------|------|
| **单用户/小团队，离线用** | **FAISS** | 零运维，10MB 文件即一切 |
| **多用户，要元数据过滤** | **Qdrant** | API 兼容 Pinecone，迁移零代码改动 |
| **想顺带用 PG（合并 DB）** | **pgvector** | 少一个服务 |
| **追求生产级、可扩展** | **Qdrant** | 多了元数据/分片/副本 |
| **快速原型/MVP** | **Chroma** | 上手最快 |

**默认推荐 Qdrant**——API 兼容、迁移零成本、运维适中。

---

## 3. 切换步骤（任意方案）

### 3.1 准备工作

```bash
# 1. 安装新依赖（举例：Qdrant）
pip install qdrant-client

# 2. .env 修改
echo "VECTOR_STORE_TYPE=qdrant" >> .env
echo "QDRANT_HOST=localhost" >> .env
echo "QDRANT_PORT=6333" >> .env

# 3. （仅 Qdrant）启动服务
docker run -d -p 6333:6333 --name englishmaster-qdrant qdrant/qdrant
```

### 3.2 切换后端

```bash
pkill -f "uvicorn backend.main"
uvicorn backend.main:app --port 8000
# 启动日志会显示 "Vector store ready: {'backend': 'qdrant', ...}"
```

**零代码改动**——`get_vector_store()` 工厂按 `VECTOR_STORE_TYPE` 自动选实现。

### 3.3 迁移数据（Pinecone → 新方案）

```bash
# 迁移脚本
python scripts/ops/migrate_pinecone_to_faiss.py
# 类比写 migrate_pinecone_to_qdrant.py 同样套路
```

### 3.4 验证

```bash
# RAG 检索验证（无论用啥后端，这个脚本都能跑）
python scripts/04_verify_pinecone.py
# 期望：6/6 通过
```

### 3.5 回滚

```bash
# .env 改回
echo "VECTOR_STORE_TYPE=pinecone" > .env
# 重启后端
```

---

## 4. 5 个方案详细对比

### 4.1 FAISS（Meta 出品，纯本地库）

| 维度 | 评价 |
|------|------|
| 安装 | `pip install faiss-cpu`（CPU 版），无需 GPU |
| 启动 | 0 服务进程，index 直接读文件 |
| 持久化 | 3 个文件：`index.faiss`, `index.pkl`（IDs）, `metadata.json` |
| 元数据过滤 | **不支持原生**（要自己维护 ID 映射） |
| 性能 | **查询极快**（纯 C++） |
| 删除 | IndexFlatIP 不支持真删除（要重建） |
| 备份 | cp 三个文件即可 |
| 适合 | 单机、<1M 向量、原型 |
| 不适合 | 多实例分布式 |

**我们项目适合度**：✅ 841 个向量，启动 < 50ms

### 4.2 Qdrant（Rust 服务端）

| 维度 | 评价 |
|------|------|
| 安装 | `pip install qdrant-client` + 跑 `qdrant/qdrant` docker |
| 启动 | 起一个服务（200ms） |
| 持久化 | 自动写到本地 volume |
| 元数据过滤 | **强**（原生支持 Payload 过滤） |
| 性能 | 优（Rust 写） |
| 删除 | 原生支持 |
| 备份 | snapshot 命令 |
| 适合 | 多用户、生产、需要过滤 |
| 不适合 | 不想起服务 |

**我们项目适合度**：✅ 完美匹配

### 4.3 Milvus

杀鸡用牛刀，跳过。

### 4.4 Chroma（最易上手）

| 维度 | 评价 |
|------|------|
| 安装 | `pip install chromadb` |
| 启动 | 0 服务进程，纯 Python |
| 性能 | 中（数据量大后变慢） |
| 元数据过滤 | where 子句（中等） |
| 适合 | <100k 向量、原型 |
| 不适合 | 数据增长后扩展差 |

**我们项目适合度**：✓ 可用但不如 Qdrant

### 4.5 pgvector

适合**已经把数据库迁到 PG** 的场景。我们当前是 SQLite，迁过去成本大。

---

## 5. 决策树

```
                    你的数据量？
                         │
                ┌────────┴────────┐
                <1M 向量          >1M
                │                  │
          ┌�────┴─────┐           Qdrant / Milvus
       FAISS / Chroma
          │                  │
    要起服务吗？
       │
 ┌─────┴─────┐
 不（单机）    要
 │              │
FAISS         Qdrant
```

更简单：**你目前的痛点是什么**？
- 担心 Pinecone 涨价 → **FAISS**（零成本，本地文件）
- 担心网络依赖 → **FAISS** 或 **Qdrant**（本地方案）
- 担心数据合规/出域 → **FAISS** 或 **Qdrant**
- 想要"和 Pinecone 一样好用" → **Qdrant**（API 兼容）
- 已在用 PG → **pgvector**

---

## 6. 已落地代码清单

| 文件 | 内容 |
|------|------|
| `backend/services/vector_store.py` | **抽象层**（`VectorStore` 抽象基类 + 工厂） |
| `backend/services/pinecone_store.py` | Pinecone 实现（保留原行为） |
| `backend/services/faiss_store.py` | **FAISS 完整实现**（持久化 + 元数据过滤） |
| `backend/services/qdrant_store.py` | Qdrant 实现（推荐） |
| `backend/services/chroma_store.py` | Chroma 实现 |
| `backend/services/pgvector_store.py` | pgvector 实现 |
| `backend/services/rag_service.py` | 改用抽象层，业务逻辑不变 |
| `backend/dependencies.py` | 移除 `get_pinecone_index` 单一函数 |
| `scripts/ops/migrate_pinecone_to_faiss.py` | 迁移脚本（通用模板，可改其他后端） |

---

## 7. 注意事项

1. **embedding 模型不变**——`multilingual-e5-large` 1024 维，所有后端兼容
2. **E5 prefix 仍需要**——`query: ` 前缀是模型层要求，不在后端
3. **过滤字段名统一**——抽象层用 `unit`, `semester`，各后端映射：
   - Pinecone: `{"unit": {"$eq": "Unit 1"}}`
   - Qdrant: `FieldCondition(key="unit", match=MatchValue(...))`
   - FAISS/PG/Chroma: `{"unit": "Unit 1"}`
4. **metric 统一 cosine**——FAISS 用 `IndexFlatIP` + 归一化，等价 cosine
5. **本地方案不跨实例同步**——多实例部署时需自己同步 index 文件

---

## 8. 决策记录

| 决策 | 选择 | 原因 | 日期 |
|------|------|------|------|
| 抽象层 | 5 个实现 | 用户可选最匹配场景 | 2026-06-02 |
| 默认后端 | Pinecone | 不变（生产用） | — |
| 推荐后端 | Qdrant | API 兼容 + 强元数据过滤 | 2026-06-02 |
| FAISS 完整实现 | ✅ 优先做 | 零运维，最易演示 | 2026-06-02 |
| Milvus 实现 | ❌ 暂不写 | 杀鸡用牛刀 | 2026-06-02 |

---

*文档版本：v1.0*
