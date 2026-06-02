.PHONY: help install dev backend frontend test test-fast test-all lint format type-check clean smoke bench docs run stop logs

# ===== 帮助 =====
help:
	@echo "EnglishMaster Agent - Makefile"
	@echo ""
	@echo "开发："
	@echo "  make install      - 装依赖"
	@echo "  make dev          - 同时启动后端 + 前端"
	@echo "  make backend      - 只启动后端"
	@echo "  make frontend     - 只启动前端"
	@echo ""
	@echo "测试："
	@echo "  make test-fast    - 只单元测试（< 30s）"
	@echo "  make test-all     - 全部测试 + 覆盖率"
	@echo "  make smoke        - 部署后冒烟（默认 http://localhost:8000）"
	@echo "  make bench        - 性能基线"
	@echo ""
	@echo "代码质量："
	@echo "  make lint         - ruff + tsc"
	@echo "  make format       - 自动格式化"
	@echo "  make type-check   - mypy"
	@echo ""
	@echo "数据流水线："
	@echo "  make data         - 跑 00a..04 + extract_vocab"
	@echo "  make eval         - 跑 AI 评价集"
	@echo ""
	@echo "运维："
	@echo "  make run          - docker compose up"
	@echo "  make stop         - docker compose down"
	@echo "  make logs         - docker compose logs"
	@echo "  make backup       - 备份 SQLite 到 S3"
	@echo "  make rollback     - 紧急回滚"

# ===== 安装 =====
install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	cd frontend && npm install && cd ..

# ===== 开发 =====
backend:
	source .venv/bin/activate && uvicorn backend.main:app --port 8000 --reload

frontend:
	cd frontend && npm run dev

dev:
	@echo "Starting backend + frontend (use 2 terminals or screen/tmux)"
	@echo "Terminal 1: make backend"
	@echo "Terminal 2: make frontend"

# ===== 测试 =====
test-fast:
	source .venv/bin/activate && pytest tests/ -x --no-cov -q -m "not slow"

test-all:
	source .venv/bin/activate && pytest tests/ --cov=backend --cov-report=term-missing

lint:
	@echo ">>> Linting backend..."
	source .venv/bin/activate && ruff check backend/ tests/
	@echo ">>> Linting frontend..."
	cd frontend && npm run lint

format:
	source .venv/bin/activate && ruff format backend/ tests/
	cd frontend && npx prettier --write "**/*.{ts,tsx,css,md}"

type-check:
	source .venv/bin/activate && mypy backend/

# ===== 数据流水线 =====
data:
	@echo "Running full data pipeline..."
	python scripts/00a_pdf_to_images.py
	python scripts/00b_ocr_with_minimax.py
	python scripts/00c_verify_ocr.py
	python scripts/02_chunk_text.py
	python scripts/03_embed_and_upload.py
	python scripts/04_verify_pinecone.py
	python scripts/extract_vocab.py
	@echo "✅ Data pipeline complete"

eval:
	@echo "Running AI evaluation suite..."
	@echo "(TODO: implement eval_rag.py, eval_chat.py, eval_quiz.py, eval_grade.py)"

# ===== 运维 =====
run:
	docker compose up -d

stop:
	docker compose down

logs:
	docker compose logs -f --tail=100

smoke:
	@if [ -z "$(BACKEND_URL)" ]; then \
		echo "Usage: make smoke BACKEND_URL=http://your-server"; \
		echo "  or: BACKEND_URL=http://localhost:8000 make smoke"; \
	else \
		./scripts/ops/smoke_test.sh $(BACKEND_URL); \
	fi

bench:
	source .venv/bin/activate && python scripts/ops/benchmark.py --rounds 20

backup:
	./scripts/backup/sqlite.sh

rollback:
	@if [ -z "$(VERSION)" ]; then \
		echo "Usage: make rollback VERSION=v3.2"; \
	else \
		./scripts/ops/rollback.sh $(VERSION); \
	fi

# ===== 清理 =====
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.log" -delete 2>/dev/null || true
	rm -rf frontend/.next
	rm -rf frontend/node_modules/.cache
	@echo "✅ Cleaned"
