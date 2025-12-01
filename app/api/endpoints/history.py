"""
API endpoints for chat history management
Provides access to conversations, messages, and analytics
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta

from app.db.models import get_db
from app.db.crud import ChatHistoryManager

router = APIRouter(prefix="/api/history", tags=["Chat History"])


@router.get("/conversations")
async def get_conversations(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=1000, description="Number of records to return"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    session_type: Optional[str] = Query(None, description="Filter by session type (user/anonymous)"),
    language: Optional[str] = Query(None, description="Filter by language code (EN/BN)"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get all conversations with pagination and filtering
    
    **Query Parameters:**
    - skip: Pagination offset (default: 0)
    - limit: Results per page (default: 20, max: 100)
    - user_id: Filter by specific user ID
    - session_type: Filter by 'user' or 'anonymous'
    - date_from: Start date filter (YYYY-MM-DD)
    - date_to: End date filter (YYYY-MM-DD)
    
    **Returns:**
    - total_conversations: Total count matching filters
    - page: Current page number
    - per_page: Results per page
    - total_pages: Total pages available
    - conversations: Array of conversation objects
    """
    try:
        # Parse dates if provided
        date_from_obj = datetime.fromisoformat(date_from) if date_from else None
        date_to_obj = datetime.fromisoformat(date_to) if date_to else None
        
        result = ChatHistoryManager.get_all_conversations(
            db=db,
            skip=skip,
            limit=limit,
            user_id=user_id,
            session_type=session_type,
            language=language,
            date_from=date_from_obj,
            date_to=date_to_obj
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching conversations: {str(e)}")


@router.get("/conversations/{conversation_id}")
async def get_conversation_messages(
    conversation_id: str,
    skip: int = Query(0, ge=0, description="Number of messages to skip"),
    limit: int = Query(50, ge=1, le=200, description="Number of messages to return"),
    role_filter: Optional[str] = Query(None, description="Filter by role (user/assistant)"),
    level_filter: Optional[str] = Query(None, description="Filter by message level"),
    category_filter: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db)
):
    """
    Get messages from a specific conversation
    
    **Path Parameters:**
    - conversation_id: Unique conversation identifier
    
    **Query Parameters:**
    - skip: Pagination offset (default: 0)
    - limit: Results per page (default: 50, max: 200)
    - role_filter: Filter by 'user' or 'assistant'
    - level_filter: Filter by 'low', 'mid', 'high', 'critical', 'sensitive'
    - category_filter: Filter by category (billing, technical, packages, etc.)
    
    **Returns:**
    - conversation_id: Conversation identifier
    - user_id: Associated user ID (if any)
    - language: Conversation language
    - total_messages: Total messages matching filters
    - page: Current page number
    - per_page: Results per page
    - total_pages: Total pages available
    - messages: Array of message objects
    """
    try:
        result = ChatHistoryManager.get_conversation_messages(
            db=db,
            conversation_id=conversation_id,
            skip=skip,
            limit=limit,
            role_filter=role_filter,
            level_filter=level_filter,
            category_filter=category_filter
        )
        
        if result["total_messages"] == 0 and not result["user_id"]:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching messages: {str(e)}")


@router.get("/users/{user_id}/conversations")
async def get_user_conversations(
    user_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get all conversations for a specific user
    
    **Path Parameters:**
    - user_id: User identifier
    
    **Query Parameters:**
    - skip: Pagination offset (default: 0)
    - limit: Results per page (default: 20, max: 1000)
    
    **Returns:**
    - Same structure as /conversations endpoint, filtered by user_id
    """
    try:
        result = ChatHistoryManager.get_user_conversations(
            db=db,
            user_id=user_id,
            skip=skip,
            limit=limit
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user conversations: {str(e)}")


@router.get("/users/{user_id}/messages")
async def get_user_all_messages(
    user_id: str,
    limit: int = Query(500, ge=1, le=1000, description="Maximum number of messages to return"),
    db: Session = Depends(get_db)
):
    """
    Get ALL messages from a user across ALL their conversations
    
    **Path Parameters:**
    - user_id: User identifier (use 'anonymous' for anonymous users)
    
    **Query Parameters:**
    - limit: Maximum messages to return (default: 500, max: 1000)
    
    **Returns:**
    - user_id: User identifier
    - total_messages: Total message count
    - conversations_count: Number of conversations
    - messages: Array of all messages with conversation info
    """
    try:
        # Get all user conversations
        if user_id.lower() == 'anonymous':
            conversations_result = ChatHistoryManager.get_all_conversations(
                db=db,
                skip=0,
                limit=1000,
                session_type='anonymous'
            )
        else:
            conversations_result = ChatHistoryManager.get_user_conversations(
                db=db,
                user_id=user_id,
                skip=0,
                limit=1000
            )
        
        all_messages = []
        for conv in conversations_result['conversations']:
            messages_result = ChatHistoryManager.get_conversation_messages(
                db=db,
                conversation_id=conv['conversation_id'],
                skip=0,
                limit=500
            )
            # Add conversation metadata to each message
            for msg in messages_result['messages']:
                msg['conversation_id'] = conv['conversation_id']
                msg['conversation_created'] = conv['created_at']
                msg['language'] = conv['language']
            all_messages.extend(messages_result['messages'])
        
        # Sort by created_at (Newest first)
        all_messages.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Limit results
        all_messages = all_messages[:limit]
        
        return {
            "user_id": user_id,
            "total_messages": len(all_messages),
            "conversations_count": len(conversations_result['conversations']),
            "messages": all_messages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user messages: {str(e)}")


@router.get("/statistics/daily")
async def get_daily_statistics(
    date: Optional[str] = Query(None, description="Specific date (YYYY-MM-DD)"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    days: int = Query(7, ge=1, le=90, description="Number of days to fetch"),
    db: Session = Depends(get_db)
):
    """
    Get daily usage statistics
    
    **Query Parameters:**
    - date: Specific date (YYYY-MM-DD) - if not provided, fetches last N days
    - user_id: Filter by specific user
    - days: Number of days to fetch (default: 7, max: 90)
    
    **Returns:**
    - Array of daily statistics including:
      - total_conversations: Number of conversations
      - total_messages: Total messages sent
      - user_messages: Messages from users
      - assistant_messages: Messages from assistant
      - total_tokens: Token usage estimate
      - message_levels: Breakdown by security level
      - total_api_calls: API calls made
      - avg_response_time_ms: Average response time
    """
    try:
        result = ChatHistoryManager.get_daily_statistics(
            db=db,
            date=date,
            user_id=user_id,
            days=days
        )
        return {"statistics": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching statistics: {str(e)}")


@router.get("/search")
async def search_messages(
    q: str = Query(..., min_length=2, description="Search term"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Search messages by content
    
    **Query Parameters:**
    - q: Search term (minimum 2 characters)
    - user_id: Optional user ID filter
    - skip: Pagination offset (default: 0)
    - limit: Results per page (default: 50, max: 200)
    
    **Returns:**
    - search_term: The search query
    - total_results: Total matching messages
    - page: Current page
    - per_page: Results per page
    - total_pages: Total pages
    - messages: Array of matching messages
    """
    try:
        result = ChatHistoryManager.search_messages(
            db=db,
            search_term=q,
            user_id=user_id,
            skip=skip,
            limit=limit
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching messages: {str(e)}")


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a conversation and all its messages
    
    **Path Parameters:**
    - conversation_id: Conversation to delete
    
    **Returns:**
    - success: Boolean indicating deletion success
    - message: Status message
    """
    try:
        success = ChatHistoryManager.delete_conversation(db, conversation_id)
        
        if success:
            return {
                "success": True,
                "message": f"Conversation {conversation_id} deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting conversation: {str(e)}")


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Check database health and get basic statistics
    
    **Returns:**
    - status: Database connection status
    - total_conversations: Total conversations in database
    - total_messages: Total messages in database
    """
    try:
        from app.db.models import Conversation, Message
        
        total_conversations = db.query(Conversation).count()
        total_messages = db.query(Message).count()
        
        return {
            "status": "healthy",
            "database": "sqlite",
            "total_conversations": total_conversations,
            "total_messages": total_messages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database health check failed: {str(e)}")
