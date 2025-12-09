"""
CRUD operations for chat history database
Optimized queries with proper filtering and pagination
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid
import json

from app.db.models import Conversation, Message, DailyStatistics


class ChatHistoryManager:
    """Manages all database operations for chat history"""
    
    @staticmethod
    def create_conversation(
        db: Session,
        user_id: Optional[str] = None,
        language: str = "EN",
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Conversation:
        """
        Create a new conversation
        Generates unique conversation_id based on user_id or anonymous pattern
        """
        # Generate conversation ID
        if user_id:
            conversation_id = f"user_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            session_type = "user"
        else:
            random_suffix = uuid.uuid4().hex[:12]
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            conversation_id = f"anonymous_{timestamp}_{random_suffix}"
            session_type = "anonymous"
        
        conversation = Conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            session_type=session_type,
            language=language,
            user_agent=user_agent,
            ip_address=ip_address,
            total_messages=0,
            total_tokens_used=0
        )
        
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        return conversation
    
    @staticmethod
    def get_or_create_conversation(
        db: Session,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        language: str = "EN",
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Conversation:
        """Get existing conversation or create new one"""
        if conversation_id:
            conversation = db.query(Conversation).filter(
                Conversation.conversation_id == conversation_id
            ).first()
            if conversation:
                return conversation
        
        return ChatHistoryManager.create_conversation(
            db, user_id, language, user_agent, ip_address
        )
    
    @staticmethod
    def add_message(
        db: Session,
        conversation_id: str,
        role: str,
        sender: str,
        content: str,
        message_level: str = "low",
        category: Optional[str] = None,
        tokens_used: int = 0,
        response_time_ms: float = 0.0,
        store: bool = True,
        tools_used: Optional[List[str]] = None,
        api_calls_made: int = 0
    ) -> Message:
        """Add a message to a conversation"""
        
        # Get conversation
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id
        ).first()
        
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        # Get next message index
        last_message = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(desc(Message.message_index)).first()
        
        message_index = (last_message.message_index + 1) if last_message else 1
        
        # Detect sensitive content
        contains_user_data = ChatHistoryManager._detect_user_data(content)
        
        # Create message
        message = Message(
            conversation_id=conversation_id,
            role=role,
            sender=sender,
            content=content,
            message_index=message_index,
            message_level=message_level,
            category=category,
            tokens_used=tokens_used,
            response_time_ms=response_time_ms,
            store=store,
            contains_user_data=contains_user_data,
            tools_used=json.dumps(tools_used) if tools_used else None,
            api_calls_made=api_calls_made
        )
        
        db.add(message)
        
        # Update conversation statistics
        conversation.total_messages += 1
        conversation.total_tokens_used += tokens_used
        conversation.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(message)
        
        # Update daily statistics
        ChatHistoryManager._update_daily_stats(db, conversation.user_id, message)
        
        return message
    
    @staticmethod
    def get_conversation_messages(
        db: Session,
        conversation_id: str,
        skip: int = 0,
        limit: int = 50,
        role_filter: Optional[str] = None,
        level_filter: Optional[str] = None,
        category_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get messages from a conversation with pagination and filters
        Returns messages and metadata
        """
        query = db.query(Message).filter(Message.conversation_id == conversation_id)
        
        # Apply filters
        if role_filter:
            query = query.filter(Message.role == role_filter)
        if level_filter:
            query = query.filter(Message.message_level == level_filter)
        if category_filter:
            query = query.filter(Message.category == category_filter)
        
        # Get total count
        total = query.count()
        
        # Get paginated messages
        messages = query.order_by(Message.message_index).offset(skip).limit(limit).all()
        
        # Get conversation info
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id
        ).first()
        
        return {
            "conversation_id": conversation_id,
            "user_id": conversation.user_id if conversation else None,
            "language": conversation.language if conversation else "EN",
            "total_messages": total,
            "page": (skip // limit) + 1,
            "per_page": limit,
            "total_pages": (total + limit - 1) // limit,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "sender": msg.sender,
                    "content": msg.content,
                    "message_index": msg.message_index,
                    "message_level": msg.message_level,
                    "category": msg.category,
                    "tokens_used": msg.tokens_used,
                    "response_time_ms": msg.response_time_ms,
                    "tools_used": json.loads(msg.tools_used) if msg.tools_used else [],
                    "api_calls_made": msg.api_calls_made,
                    "created_at": msg.created_at.isoformat()
                }
                for msg in messages
            ]
        }
    
    @staticmethod
    def get_all_conversations(
        db: Session,
        skip: int = 0,
        limit: int = 20,
        user_id: Optional[str] = None,
        session_type: Optional[str] = None,
        language: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get all conversations with pagination and filters"""
        query = db.query(Conversation)
        
        # Apply filters
        if user_id:
            query = query.filter(Conversation.user_id == user_id)
        if session_type:
            query = query.filter(Conversation.session_type == session_type)
        if language:
            query = query.filter(Conversation.language == language)
        if date_from:
            query = query.filter(Conversation.created_at >= date_from)
        if date_to:
            query = query.filter(Conversation.created_at <= date_to)
        
        # Get total count
        total = query.count()
        
        # Get paginated conversations
        conversations = query.order_by(desc(Conversation.updated_at)).offset(skip).limit(limit).all()
        
        return {
            "total_conversations": total,
            "page": (skip // limit) + 1,
            "per_page": limit,
            "total_pages": (total + limit - 1) // limit,
            "conversations": [
                {
                    "conversation_id": conv.conversation_id,
                    "user_id": conv.user_id,
                    "session_type": conv.session_type,
                    "language": conv.language,
                    "total_messages": conv.total_messages,
                    "total_tokens_used": conv.total_tokens_used,
                    "created_at": conv.created_at.isoformat(),
                    "updated_at": conv.updated_at.isoformat()
                }
                for conv in conversations
            ]
        }
    
    @staticmethod
    def get_user_conversations(
        db: Session,
        user_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get all conversations for a specific user"""
        return ChatHistoryManager.get_all_conversations(
            db, skip, limit, user_id=user_id
        )

    @staticmethod
    def get_user_messages_paginated(
        db: Session,
        user_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Return paginated messages across all conversations for a user"""
        # Build base query joining conversations for metadata in one trip
        base_query = db.query(Message, Conversation).join(
            Conversation, Conversation.conversation_id == Message.conversation_id
        )

        if user_id.lower() == "anonymous":
            base_query = base_query.filter(Conversation.session_type == "anonymous")
        else:
            base_query = base_query.filter(Conversation.user_id == user_id)

        total_messages = base_query.count()
        conversations_count = base_query.with_entities(
            Conversation.conversation_id
        ).distinct().count()

        results = (
            base_query.order_by(Message.created_at)
            .offset(skip)
            .limit(limit)
            .all()
        )

        messages = []
        for msg, conv in results:
            messages.append(
                {
                    "id": msg.id,
                    "conversation_id": msg.conversation_id,
                    "role": msg.role,
                    "sender": msg.sender,
                    "content": msg.content,
                    "message_index": msg.message_index,
                    "message_level": msg.message_level,
                    "category": msg.category,
                    "tokens_used": msg.tokens_used,
                    "response_time_ms": msg.response_time_ms,
                    "tools_used": json.loads(msg.tools_used) if msg.tools_used else [],
                    "api_calls_made": msg.api_calls_made,
                    "created_at": msg.created_at.isoformat(),
                    "conversation_created": conv.created_at.isoformat() if conv else None,
                    "language": conv.language if conv else None,
                }
            )

        return {
            "user_id": user_id,
            "total_messages": total_messages,
            "conversations_count": conversations_count,
            "page": (skip // limit) + 1,
            "per_page": limit,
            "total_pages": (total_messages + limit - 1) // limit,
            "has_more": (skip + limit) < total_messages,
            "next_skip": (skip + limit) if (skip + limit) < total_messages else None,
            "messages": messages,
        }
    
    @staticmethod
    def get_daily_statistics(
        db: Session,
        date: Optional[str] = None,
        user_id: Optional[str] = None,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get daily statistics for analytics"""
        query = db.query(DailyStatistics)
        
        if user_id:
            query = query.filter(DailyStatistics.user_id == user_id)
        
        if date:
            query = query.filter(DailyStatistics.date == date)
        else:
            # Get last N days
            start_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
            query = query.filter(DailyStatistics.date >= start_date)
        
        stats = query.order_by(desc(DailyStatistics.date)).all()
        
        return [
            {
                "date": stat.date,
                "user_id": stat.user_id,
                "total_conversations": stat.total_conversations,
                "total_messages": stat.total_messages,
                "user_messages": stat.user_messages,
                "assistant_messages": stat.assistant_messages,
                "total_tokens": stat.total_tokens,
                "message_levels": {
                    "low": stat.low_level_count,
                    "mid": stat.mid_level_count,
                    "high": stat.high_level_count,
                    "critical": stat.critical_level_count,
                    "sensitive": stat.sensitive_level_count
                },
                "total_api_calls": stat.total_api_calls,
                "avg_response_time_ms": stat.avg_response_time_ms
            }
            for stat in stats
        ]
    
    @staticmethod
    def _update_daily_stats(db: Session, user_id: Optional[str], message: Message):
        """Update daily statistics after adding a message"""
        today = datetime.utcnow().strftime('%Y-%m-%d')
        
        # Get or create daily stats
        stats = db.query(DailyStatistics).filter(
            and_(
                DailyStatistics.date == today,
                DailyStatistics.user_id == user_id
            )
        ).first()
        
        if not stats:
            stats = DailyStatistics(date=today, user_id=user_id)
            db.add(stats)
            db.flush()  # Flush to get default values set
        
        # Update counts (handle None values)
        stats.total_messages = (stats.total_messages or 0) + 1
        if message.role == "user":
            stats.user_messages = (stats.user_messages or 0) + 1
        else:
            stats.assistant_messages = (stats.assistant_messages or 0) + 1
        
        stats.total_tokens = (stats.total_tokens or 0) + message.tokens_used
        stats.total_api_calls = (stats.total_api_calls or 0) + message.api_calls_made
        
        # Update message level counts
        level_map = {
            "low": "low_level_count",
            "mid": "mid_level_count",
            "high": "high_level_count",
            "critical": "critical_level_count",
            "sensitive": "sensitive_level_count"
        }
        if message.message_level in level_map:
            current = getattr(stats, level_map[message.message_level]) or 0
            setattr(stats, level_map[message.message_level], current + 1)
        
        # Update average response time (only for assistant messages)
        if message.role == "assistant" and message.response_time_ms > 0:
            current_avg = stats.avg_response_time_ms or 0.0
            current_count = stats.assistant_messages or 0
            # Calculate new average before incrementing count
            if current_count > 0:
                total_response_time = current_avg * current_count
                stats.avg_response_time_ms = (total_response_time + message.response_time_ms) / (current_count + 1)
            else:
                stats.avg_response_time_ms = message.response_time_ms
        
        db.commit()
    
    @staticmethod
    def _detect_user_data(content: str) -> bool:
        """Detect if message contains sensitive user data"""
        sensitive_keywords = [
            'password', 'credit card', 'ssn', 'social security',
            'bank account', 'pin', 'cvv', 'passport'
        ]
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in sensitive_keywords)
    
    @staticmethod
    def delete_conversation(db: Session, conversation_id: str) -> bool:
        """Delete a conversation and all its messages"""
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id
        ).first()
        
        if conversation:
            db.delete(conversation)
            db.commit()
            return True
        return False

    @staticmethod
    def delete_message(db: Session, message_id: int) -> bool:
        """Delete a single message and update conversation counters"""
        message = db.query(Message).filter(Message.id == message_id).first()
        if not message:
            return False

        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == message.conversation_id
        ).first()

        # Remove message and keep conversation metadata consistent
        db.delete(message)
        if conversation:
            conversation.total_messages = max((conversation.total_messages or 1) - 1, 0)
            conversation.total_tokens_used = max(
                (conversation.total_tokens_used or 0) - (message.tokens_used or 0), 0
            )
            conversation.updated_at = datetime.utcnow()

        db.commit()
        return True

    @staticmethod
    def delete_user_messages(db: Session, user_id: str) -> Dict[str, Any]:
        """Delete all conversations and messages for a user (or anonymous pool)"""
        if user_id.lower() == "anonymous":
            conversations = db.query(Conversation).filter(Conversation.session_type == "anonymous").all()
        else:
            conversations = db.query(Conversation).filter(Conversation.user_id == user_id).all()

        if not conversations:
            return {"deleted_conversations": 0, "deleted_messages": 0}

        deleted_messages = 0
        for conv in conversations:
            deleted_messages += len(conv.messages)
            db.delete(conv)

        # Clear daily statistics for this user/anonymous bucket
        stats_query = db.query(DailyStatistics)
        if user_id.lower() == "anonymous":
            stats_query = stats_query.filter(DailyStatistics.user_id.is_(None))
        else:
            stats_query = stats_query.filter(DailyStatistics.user_id == user_id)
        stats_query.delete(synchronize_session=False)

        db.commit()

        return {
            "deleted_conversations": len(conversations),
            "deleted_messages": deleted_messages
        }

    @staticmethod
    def purge_all_data(db: Session) -> Dict[str, int]:
        """Remove all conversations, messages, and daily statistics"""
        total_messages = db.query(Message).count()
        total_conversations = db.query(Conversation).count()
        total_stats = db.query(DailyStatistics).count()

        db.query(Message).delete(synchronize_session=False)
        db.query(Conversation).delete(synchronize_session=False)
        db.query(DailyStatistics).delete(synchronize_session=False)
        db.commit()

        return {
            "deleted_messages": total_messages,
            "deleted_conversations": total_conversations,
            "deleted_stats": total_stats
        }
    
    @staticmethod
    def search_messages(
        db: Session,
        search_term: str,
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Search messages by content"""
        query = db.query(Message).filter(
            Message.content.like(f"%{search_term}%")
        )
        
        if user_id:
            query = query.join(Conversation).filter(Conversation.user_id == user_id)
        
        total = query.count()
        messages = query.order_by(desc(Message.created_at)).offset(skip).limit(limit).all()
        
        return {
            "search_term": search_term,
            "total_results": total,
            "page": (skip // limit) + 1,
            "per_page": limit,
            "total_pages": (total + limit - 1) // limit,
            "messages": [
                {
                    "id": msg.id,
                    "conversation_id": msg.conversation_id,
                    "role": msg.role,
                    "content": msg.content,
                    "message_level": msg.message_level,
                    "created_at": msg.created_at.isoformat()
                }
                for msg in messages
            ]
        }
