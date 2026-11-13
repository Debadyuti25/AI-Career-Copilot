from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "mysql+pymysql://2tVXTrPScYrDgVh.root:DVe5WyDGhHQQAc3s@gateway01.ap-northeast-1.prod.aws.tidbcloud.com:4000/test"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"ssl": {"ssl": True}}
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()
