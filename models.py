from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String(150), unique=True, nullable=False)
    password = Column(String(150), nullable=False)

class Report(Base):
    __tablename__ = 'reports'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    resume_text = Column(Text)  
    role = Column(String(100))
    result = Column(Text) 
    created_at = Column(DateTime, default=datetime.now)
    
    user = relationship("User")

# DB Connection
engine = create_engine('sqlite:///database.db')
Base.metadata.create_all(engine)