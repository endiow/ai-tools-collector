# -*- coding: utf-8 -*-
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, Date, DateTime, Text,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from config import DATABASE_URL

Base = declarative_base()


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    hash = Column(String(32), unique=True, index=True)   # md5(full_name)
    full_name = Column(String(256), index=True)
    name = Column(String(256))
    owner = Column(String(128))
    url = Column(String(512))
    description = Column(Text)
    language = Column(String(64))
    stars = Column(Integer, default=0)
    forks = Column(Integer, default=0)
    stars_today = Column(String(32))      # 日榜：今日新增 Star
    stars_week = Column(String(32))       # 周榜：本周新增 Star
    period = Column(String(32), default="daily", index=True)  # "daily" / "weekly" / "daily,weekly"
    is_ai = Column(Boolean, default=False, index=True)
    category = Column(String(64))
    domain = Column(String(64))
    ai_summary = Column(Text)
    license_type = Column(String(64))
    collected_date = Column(Date, index=True)
    created_at = Column(DateTime, default=datetime.now)


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(engine)