<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# Repository Guidelines

- **语言**：所有对话与说明一律使用中文。

## 项目结构与模块组织
- `app/` 为 FastAPI 应用主体：`api/` 路由、`services/` 业务逻辑、`models/` 与 `schemas/` 数据模型与校验、`core/` 配置与安全、`utils/` 工具函数。
- `alembic/` 与 `alembic.ini` 用于数据库迁移；版本文件在 `alembic/versions/`。
- `scripts/` 为运维脚本；`requirements.txt`/`pyproject.toml` 定义依赖。

## 构建、测试与开发命令
- `python -m venv venv` 并激活虚拟环境用于本地开发。
- `pip install -r requirements.txt` 安装运行依赖。
- `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` 本地启动 API。
- Alembic 流程：`alembic revision --autogenerate -m "..."` 生成迁移，`alembic upgrade head` 执行；`alembic current` 查看状态。

## 编码风格与命名约定
- Python 3.10+；遵循 PEP 8，4 空格缩进。
- 模块、函数、变量使用 `snake_case`；类使用 `PascalCase`。
- API 端点文件位于 `app/api/api_v1/endpoints/`，文件名用复数（如 `questions.py`）。
- 未配置格式化或 lint 工具；保持改动紧凑并与现有代码风格一致。

## 测试规范
- 开发依赖包含 `pytest`，但当前尚无完整测试套件。
- 建议在 `tests/` 或 `app/tests/` 下新增测试，文件命名为 `test_*.py`。
- 测试命令：`pytest`。

## 提交与拉取请求规范
- 提交信息常见为简短 `update`，也有 `fix:`/`feat:`/`refactor` 等前缀，并可能带 `fixes #<id>`。
- 提交信息保持简洁、范围清晰；有对应问题时附带编号。
- PR 需描述行为变化、注明迁移影响并关联问题；若变更接口，补充 API 示例。

## 配置与安全
- 配置从 `.env` 读取，见 `app/core/config.py`。优先使用 `DATABASE_URL`，否则设置 `POSTGRES_*`。
- 秘钥（API Key、JWT `SECRET_KEY`）不要提交到仓库；使用本地 `.env` 或部署密钥管理。
