from fastapi import APIRouter, HTTPException, Depends, Request, Query
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, AIMessage
from app.models.schemas import ChatRequest, ChatResponse
from app.services.agent import process_chat
from app.db.models import get_db
from app.db.crud import ChatHistoryManager
import time

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """
    API Endpoint to chat with the ISP Assistant.
    Now saves all messages to SQLite database with full analytics.
    
    Parameters:
    - message: User's message
    - conversation_id: Optional conversation identifier (auto-generated if not provided)
    - user_id: Optional user ID (if provided, AI won't ask for it)
    - language: Optional language preference (EN or BN, default: EN)
    
    Returns:
    - response: AI assistant's reply
    - conversation_id: Conversation identifier for continuing the chat
    """
    start_time = time.time()
    
    try:
        print(f"\n\033[93m🌍 API Request received from client: {request.message}\033[0m")
        
        # Get or create conversation
        conversation = ChatHistoryManager.get_or_create_conversation(
            db=db,
            conversation_id=request.conversation_id,
            user_id=request.user_id,
            language=request.language,
            user_agent=http_request.headers.get("user-agent"),
            ip_address=http_request.client.host if http_request.client else None
        )
        
        # Fetch recent chat history for context
        chat_history = []
        if conversation.conversation_id:
            # Get last 10 messages (excluding the one we are about to add)
            recent_messages = ChatHistoryManager.get_conversation_messages(
                db=db,
                conversation_id=conversation.conversation_id,
                limit=10
            )
            
            # Convert to LangChain format
            # Note: get_conversation_messages returns oldest first due to order_by(Message.message_index)
            for msg in recent_messages.get("messages", []):
                if msg["role"] == "user":
                    chat_history.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    chat_history.append(AIMessage(content=msg["content"]))
        
        # Save user message to database
        # Classify message level based on content
        from app.services.agent import history_manager
        msg_level = history_manager._classify_message_level(request.message)
        msg_category = history_manager._detect_category(request.message)
        
        user_message = ChatHistoryManager.add_message(
            db=db,
            conversation_id=conversation.conversation_id,
            role="user",
            sender="user",
            content=request.message,
            message_level=msg_level,
            category=msg_category,
            store=True
        )
        
        print(f"💾 User message saved to database (ID: {user_message.id})")
        
        # Process chat with AI
        ai_response = await process_chat(
            message=request.message,
            conversation_id=conversation.conversation_id,
            user_id=request.user_id,
            language=request.language,
            chat_history=chat_history
        )
        
        # Extract reply and metadata from AI response
        ai_reply = ai_response.get("reply", "")
        metadata = ai_response.get("metadata", {})
        analysis = ai_response.get("analysis", {})
        
        # Save assistant message to database
        assistant_message = ChatHistoryManager.add_message(
            db=db,
            conversation_id=conversation.conversation_id,
            role=metadata.get("role", "assistant"),
            sender=metadata.get("sender", "assistant"),
            content=ai_reply,
            message_level=analysis.get("message_level", "low"),
            category=analysis.get("category"),
            tokens_used=analysis.get("tokens_estimated", 0),
            response_time_ms=analysis.get("response_time_ms", 0),
            store=metadata.get("store", True),
            tools_used=None,  # Could extract from agent response if needed
            api_calls_made=0  # Could track if needed
        )
        
        print(f"💾 Assistant message saved to database (ID: {assistant_message.id})")
        print(f"\033[93m✅ Response sent successfully to client: {ai_reply}\033[0m\n")
        
        # Return response with conversation ID
        return ChatResponse(
            response=ai_reply,
            conversation_id=conversation.conversation_id
        )
        
    except Exception as e:
        print(f"\n❌ ERROR in chat endpoint: {str(e)}\n")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/history/{user_id}")
async def get_user_chat_history(
    user_id: str,
    limit: int = Query(500, ge=1, le=1000, description="Maximum messages to return"),
    db: Session = Depends(get_db)
):
    """
    Get complete chat history for a user by user_id ONLY.
    No conversation_id needed - returns ALL messages from ALL conversations.
    
    This is the simple endpoint - just provide user_id and get everything.
    """
    try:
        # Get all conversations for this user
        conversations = ChatHistoryManager.get_user_conversations(
            db=db,
            user_id=user_id,
            skip=0,
            limit=1000
        )
        
        if not conversations['conversations']:
            return {
                "user_id": user_id,
                "total_messages": 0,
                "total_conversations": 0,
                "messages": []
            }
        
        all_messages = []
        for conv in conversations['conversations']:
            messages = ChatHistoryManager.get_conversation_messages(
                db=db,
                conversation_id=conv['conversation_id'],
                skip=0,
                limit=500
            )
            
            # Add conversation context to each message
            for msg in messages['messages']:
                msg['conversation_id'] = conv['conversation_id']
                msg['conversation_started'] = conv['created_at']
                msg['conversation_language'] = conv['language']
            
            all_messages.extend(messages['messages'])
        
        # Sort by creation time (chronological order)
        all_messages.sort(key=lambda x: x['created_at'])
        
        # Limit total messages
        all_messages = all_messages[:limit]
        
        return {
            "user_id": user_id,
            "total_messages": len(all_messages),
            "total_conversations": len(conversations['conversations']),
            "messages": all_messages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching chat history: {str(e)}")
