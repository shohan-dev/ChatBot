"""
SQLite Database Models for Chat History
Optimized structure with proper indexing and relationships
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os

Base = declarative_base()


class Conversation(Base):
    """
    Stores conversation-level metadata
    One conversation contains multiple messages
    """
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(String(50), nullable=True, index=True)  # Nullable for anonymous users
    session_type = Column(String(50), default='anonymous')  # 'user' or 'anonymous'
    language = Column(String(10), default='EN')
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Analytics
    total_messages = Column(Integer, default=0)
    total_tokens_used = Column(Integer, default=0)
    
    # Metadata
    user_agent = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    # Relationship
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_updated', 'updated_at'),
    )


class Message(Base):
    """
    Stores individual messages within conversations
    Includes analytics and classification metadata
    """
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(255), ForeignKey('conversations.conversation_id'), nullable=False, index=True)
    
    # Message content
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    sender = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    message_index = Column(Integer, nullable=False)  # Order within conversation
    
    # Classification
    message_level = Column(String(20), default='low')  # 'low', 'mid', 'high', 'critical', 'sensitive'
    category = Column(String(50), nullable=True)  # e.g., 'billing', 'technical', 'general'
    
    # Analytics
    tokens_used = Column(Integer, default=0)
    response_time_ms = Column(Float, default=0.0)
    
    # Flags
    store = Column(Boolean, default=True)
    contains_user_data = Column(Boolean, default=False)
    requires_follow_up = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Tool usage tracking
    tools_used = Column(Text, nullable=True)  # JSON string of tools called
    api_calls_made = Column(Integer, default=0)
    
    # Relationship
    conversation = relationship("Conversation", back_populates="messages")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_conv_index', 'conversation_id', 'message_index'),
        Index('idx_role_level', 'role', 'message_level'),
        Index('idx_created', 'created_at'),
        Index('idx_category', 'category'),
    )


class DailyStatistics(Base):
    """
    Aggregated statistics per user per day
    For quick analytics without scanning all messages
    """
    __tablename__ = 'daily_statistics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    user_id = Column(String(50), nullable=True, index=True)
    
    # Counts
    total_conversations = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)
    user_messages = Column(Integer, default=0)
    assistant_messages = Column(Integer, default=0)
    
    # Token usage
    total_tokens = Column(Integer, default=0)
    
    # Message levels breakdown
    low_level_count = Column(Integer, default=0)
    mid_level_count = Column(Integer, default=0)
    high_level_count = Column(Integer, default=0)
    critical_level_count = Column(Integer, default=0)
    sensitive_level_count = Column(Integer, default=0)
    
    # API usage
    total_api_calls = Column(Integer, default=0)
    
    # Average response time
    avg_response_time_ms = Column(Float, default=0.0)
    
    __table_args__ = (
        Index('idx_date_user', 'date', 'user_id'),
    )


# Database connection and session management
DATABASE_URL = "sqlite:///./data/chat_history.db"
engine = None
SessionLocal = None


def init_db():
    """Initialize database and create all tables"""
    global engine, SessionLocal
    
    # Ensure data directory exists
    os.makedirs("./data", exist_ok=True)
    
    # Create engine
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # Needed for SQLite
        echo=False  # Set to True for SQL debugging
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    print("✅ Database initialized successfully")
    return engine


def get_db():
    """Dependency to get database session"""
    if SessionLocal is None:
        init_db()
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
