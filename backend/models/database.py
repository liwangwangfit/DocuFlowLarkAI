"""
数据库模型和配置
"""
from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import String, Integer, DateTime, Text, JSON, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from config import get_config

# 创建异步引擎
config = get_config()
engine = create_async_engine(
    config.database_url,
    echo=config.debug
)

async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class TaskModel(Base):
    """任务模型"""
    __tablename__ = "tasks"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, running, completed, error, cancelled
    progress: Mapped[int] = mapped_column(Integer, default=0)
    template_id: Mapped[str] = mapped_column(String(100), nullable=True)
    target_space_id: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    files: Mapped[dict] = mapped_column(JSON, default=list)
    results: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)


class DocumentModel(Base):
    """文档模型"""
    __tablename__ = "documents"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36))
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    file_size: Mapped[int] = mapped_column(Integer)
    file_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), default="pending")
    converted_content: Mapped[str] = mapped_column(Text, nullable=True)
    processed_content: Mapped[str] = mapped_column(Text, nullable=True)
    feishu_doc_id: Mapped[str] = mapped_column(String(100), nullable=True)
    feishu_node_token: Mapped[str] = mapped_column(String(100), nullable=True)
    quality_score: Mapped[int] = mapped_column(Integer, nullable=True)
    classification: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    meta_data: Mapped[dict] = mapped_column(JSON, default=dict)


async def init_db():
    """初始化数据库"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
