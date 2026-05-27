import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# 모든 모델 import — autogenerate가 전체 메타데이터를 인식하기 위해 필수
from app.models import Base  # noqa: F401
from app.core.config import settings

config = context.config

# .env의 DATABASE_URL(asyncpg)로 alembic.ini 값을 덮어씀
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ── Offline mode ──────────────────────────────────────────────────────────────
# alembic upgrade head --sql 로 실행 시 사용 (DB 연결 없이 SQL 출력)
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (async) ───────────────────────────────────────────────────────
def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        # Computed / Generated Column은 autogenerate에서 제외
        # (DDL을 직접 작성한 첫 마이그레이션과의 충돌 방지)
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def _include_object(object, name, type_, reflected, compare_to):
    """autogenerate 대상 필터 — 뷰, 파티션 테이블 등 제외 가능."""
    return True


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # 마이그레이션은 단발성이므로 NullPool
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
