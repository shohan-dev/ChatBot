import os
import json
import re
from typing import List, Dict, Optional
from datetime import datetime
import hashlib
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from app.core.config import settings
from app.services.tools import isp_tools


# --- History Management (deprecated - moved to SQLite) ---
# Kept for backward compatibility during transition
class HistoryManager:
    """Legacy history manager - now using SQLite database"""
    def __init__(self, base_dir: str = "data"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        print("⚠️  Legacy HistoryManager - Switch to SQLite database")

    def _classify_message_level(self, message: str) -> str:
        """
        Classify message sensitivity level
        - sensitive: Contains sensitive financial/personal data  
        - critical: Account operations, billing info
        - high: Technical support, troubleshooting
        - mid: Package inquiries
        - low: General inquiries, greetings
        """
        message_lower = message.lower()
        
        # Sensitive keywords
        sensitive_keywords = ['password', 'pin', 'credit card', 'bank', 'nid', 'account number', 'cvv']
        if any(keyword in message_lower for keyword in sensitive_keywords):
            return "sensitive"
        
        # Critical keywords
        critical_keywords = ['payment', 'bill', 'money', 'expire', 'disconnect', 'due']
        if any(keyword in message_lower for keyword in critical_keywords):
            return "critical"
        
        # High level keywords
        high_keywords = ['internet', 'connection', 'router', 'speed', 'not working', 'problem', 'issue']
        if any(keyword in message_lower for keyword in high_keywords):
            return "high"
        
        # Mid level keywords
        mid_keywords = ['package', 'subscription', 'plan', 'upgrade', 'movie', 'server']
        if any(keyword in message_lower for keyword in mid_keywords):
            return "mid"
        
        # Default to low
        return "low"

    def _detect_category(self, message: str) -> str:
        """Detect message category for better organization"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['bill', 'payment', 'money', 'due', 'pay']):
            return "billing"
        elif any(word in message_lower for word in ['internet', 'connection', 'router', 'speed', 'not working']):
            return "technical"
        elif any(word in message_lower for word in ['package', 'plan', 'subscription', 'upgrade']):
            return "packages"
        elif any(word in message_lower for word in ['movie', 'server', 'ftp', 'ott', 'stream']):
            return "entertainment"
        elif any(word in message_lower for word in ['account', 'user id', 'profile', 'details']):
            return "account"
        else:
            return "general"


history_manager = HistoryManager()



# --- Agent Setup ---

llm = ChatGoogleGenerativeAI(
    model=settings.MODEL_NAME,
    google_api_key=settings.GEMINI_API_KEY,
    temperature=0.7,
    convert_system_message_to_human=True,
    max_output_tokens=300  # Increased for JSON structure
)

# Updated System Prompt for Structured JSON Output
system_prompt = """You are ISP PayBD Assistant - an AI assistant running inside a FastAPI backend.

**CRITICAL: You MUST ALWAYS return responses in this EXACT JSON structure:**

{{
    "reply": "Your helpful message here",
    "metadata": {{
        "role": "assistant",
        "sender": "assistant",
        "store": true
    }}
}}

**JSON Rules:**
1. ALWAYS return valid JSON - never break the structure
2. NEVER include extra fields beyond reply and metadata
3. Put your entire response in the "reply" field
4. Never escape or encode messages - write them normally in the reply field
5. If user says "do not store this" or similar, set store to false, otherwise ALWAYS true
6. For code, put it inside the reply field only
7. Keep role and sender as "assistant" always

**User ID Context:**
- If you see [CONTEXT: User ID is XXXXX], use that ID automatically for ALL tool calls
- NEVER ask for user ID if it's provided in context
- If no user ID in context, ask politely in reply: "Could you share your User ID?"

**Language Preference:**
- If [LANGUAGE: Respond in Bangla], respond in Bangla/Bengali
- If [LANGUAGE: Respond in English], respond in English
- Match the user's language naturally

**ONLY Answer ISP-Related Questions:**
- Internet connectivity, billing, packages, account status, router issues
- Movie/FTP servers and OTT platforms
- If NOT ISP-related, reply:
  EN: "I'm here for ISP PayBD services! 😊 I can help with internet, billing, packages, or movie servers."
  BN: "আমি ISP PayBD সার্ভিসের জন্য আছি! 😊 ইন্টারনেট, বিলিং, প্যাকেজ বা মুভি সার্ভার নিয়ে সাহায্য করতে পারি।"

**Troubleshooting & Ticket Rules:**
1. **Internet Issues:**
   - FIRST, always use `check_internet_connectivity`.
   - If the tool suggests a fix (like "Restart Router"), ask the user to try that FIRST.
   - Say: "I see an issue. Please try restarting your router (unplug for 30s). Does that help?"

2. **Escalation (Creating Tickets):**
   - ONLY offer a ticket if:
     a) The user says the troubleshooting steps didn't work.
     b) The tool shows a critical error (like "Account Inactive" or "Payment Due").
     c) The user explicitly asks for "support" or "human agent".
   - Ask: "It seems I can't fix this remotely. Should I create a priority support ticket for our team to check?"

3. **Ticket Creation:**
   - If user says "Yes":
     - CALL `create_ticket` tool IMMEDIATELY.
     - INFER subject/category/priority from context (DO NOT ask user).
     - After tool success, give a warm, reassuring response: "I've created a ticket! 🎫 Our team has been notified and will contact you very shortly to fix this. Thanks for your patience!"

**Response Style:** Friendly, warm, helpful. Keep replies under 100 words (except movie server lists).

**Tools Available:**
- search_user_by_id (use user_id from context)
- check_internet_connectivity (use user_id from context)
- view_packages (use user_id from context)
- view_movie_servers (use user_id from context)
- create_ticket (INFER details from context, do not ask user)

**Example Response:**

User: "hi"
You return:
{{
    "reply": "Hello! 👋 How can I help you today?",
    "metadata": {{
        "role": "assistant",
        "sender": "assistant",
        "store": true
    }}
}}

User: "what's my bill?"
You return:
{{
    "reply": "I'd be happy to check your billing! Could you share your User ID?",
    "metadata": {{
        "role": "assistant",
        "sender": "assistant",
        "store": true
    }}
}}

**Contact Info (when needed):**
📞 +8801781808231 | 📧 info@isppaybd.com | 🌐 www.isppaybd.com

Always follow these instructions carefully.
Try to be concise and clear.
Try to always answer and not give an empty response. Answer in the user's preferred language.


REMEMBER: ALWAYS return valid JSON. The backend depends on this structure to save messages correctly.
"""

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)

agent = create_tool_calling_agent(llm, isp_tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=isp_tools, verbose=True)

async def process_chat(
    message: str, 
    conversation_id: Optional[str] = None,
    user_id: Optional[str] = None, 
    language: str = "EN",
    chat_history: List = []
) -> Dict[str, any]:
    """
    Process chat message and return structured response with metadata
    
    Args:
        message: User's message
        conversation_id: Unique conversation identifier (will be auto-generated if needed)
        user_id: Optional user ID for context
        language: Language preference (EN or BN)
        chat_history: List of previous messages for context
    
    Returns:
        Dict containing:
        - reply: AI assistant message
        - metadata: Message metadata for database storage
        - conversation_id: Conversation identifier
        - analysis: Message analysis (level, category, etc.)
    """
    start_time = time.time()
    
    # Classify message
    msg_level = history_manager._classify_message_level(message)
    msg_category = history_manager._detect_category(message)
    
    # Log incoming request
    print("\n" + "="*80)
    print(f"\033[93m📥 INCOMING REQUEST (Yellow Log)\033[0m")
    print("="*80)
    print(f"🆔 Conversation ID: {conversation_id if conversation_id else 'New conversation'}")
    print(f"👤 User ID: {user_id if user_id else 'Anonymous'}")
    print(f"🌐 Language: {language}")
    print(f"🔒 Security Level: {msg_level.upper()}")
    print(f"📂 Category: {msg_category}")
    print(f"\033[93m💬 User Message: {message}\033[0m")
    print(f"📚 History Depth: {len(chat_history)} messages")
    print("="*80 + "\n")
    
    # Build context with user_id and language if provided
    context_message = ""
    if user_id:
        context_message = f"[CONTEXT: User ID is {user_id}. Use this automatically for tools without asking.]"
        print(f"✅ Auto-Context: User ID {user_id} will be used automatically\n")
    
    language_instruction = f"[LANGUAGE: Respond in {'Bangla' if language == 'BN' else 'English'}]"
    print(f"🌐 Language: {'Bangla/Bengali' if language == 'BN' else 'English'} selected\n")
    
    # Prepend context to user message
    enhanced_message = f"{context_message} {language_instruction} {message}"

    # Invoke Agent
    print("🤖 AI Processing...\n")
    try:
        response = await agent_executor.ainvoke({
            "input": enhanced_message,
            "chat_history": chat_history
        })
        
        raw_output = response["output"]
        print(f"\033[93m📝 Raw AI Output: {raw_output}\033[0m")
        
        ai_reply = ""
        metadata = {}

        # Clean markdown
        clean_text = raw_output.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()

        ai_reply = ""
        metadata = {}
        
        # --- FAIL-SAFE PARSING LOGIC ---
        
        # 1. Try Standard JSON Parsing
        try:
            # Find the first '{' and last '}' to handle extra text
            start = clean_text.find('{')
            end = clean_text.rfind('}')
            if start != -1 and end != -1:
                json_candidate = clean_text[start:end+1]
                # Fix trailing commas
                json_candidate = re.sub(r',\s*([}\]])', r'\1', json_candidate)
                data = json.loads(json_candidate)
                ai_reply = data.get("reply", "")
                metadata = data.get("metadata", {})
            else:
                ai_reply = clean_text
        except json.JSONDecodeError:
            # 2. Regex Fallback (Extract text inside "reply": "...")
            # Matches: "reply": "TEXT" (handles newlines and escaped quotes)
            match = re.search(r'"reply":\s*"(.*?)(?<!\\)"', clean_text, re.DOTALL)
            if match:
                ai_reply = match.group(1)
                # Unescape
                ai_reply = ai_reply.replace('\\"', '"').replace('\\n', '\n')
            else:
                ai_reply = clean_text

        # 3. Double-Check: Did we get a JSON string back? (The "Screenshot Issue")
        # If ai_reply still looks like {"reply": "..."}, force extract the text
        if isinstance(ai_reply, str) and ai_reply.strip().startswith('{') and '"reply":' in ai_reply:
            print("⚠️ Detected raw JSON in reply. Forcing extraction.")
            # Try to grab just the text value using a loose regex
            clean_match = re.search(r'"reply":\s*"(.*?)"', ai_reply, re.DOTALL)
            if clean_match:
                ai_reply = clean_match.group(1)
            else:
                # If regex fails, just strip the braces as a last resort
                ai_reply = ai_reply.replace('{', '').replace('}', '').replace('"reply":', '').strip().strip('"')

        # 4. FAIL-SAFE: If ai_reply is empty, REVERT to raw_output
        # This ensures we NEVER show "Sorry..." if the AI actually generated text.
        if not ai_reply or not ai_reply.strip():
            if raw_output.strip():
                print("⚠️ Parsing resulted in empty string. Reverting to raw output.")
                ai_reply = raw_output
            else:
                # Only use this if the AI truly returned NOTHING
                ai_reply = "দুঃখিত, আমি উত্তর তৈরি করতে পারিনি। দয়া করে আবার চেষ্টা করুন।"

        # Final cleanup of escaped newlines
        ai_reply = ai_reply.replace('\\n', '\n').strip()

        # Ensure metadata defaults
        if not metadata:
            metadata = {"role": "assistant", "sender": "assistant", "store": True}
            
        # Final fallback if empty
        if not ai_reply or not str(ai_reply).strip():
            ai_reply = "I apologize, Please try asking again."
            if language == "BN":
                ai_reply = "দুঃখিত, দয়া করে আবার চেষ্টা করুন।"
        
        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000
        
        # Log AI response
        print("\n" + "="*80)
        print(f"\033[93m📤 AI RESPONSE (Yellow Log)\033[0m")
        print("="*80)
        print(f"✅ Status: Success")
        print(f"⏱️  Response Time: {response_time_ms:.2f}ms")
        print(f"📏 Response Length: {len(ai_reply)} characters")
        print(f"🔒 Security Level: {msg_level.upper()}")
        print(f"📂 Category: {msg_category}")
        print(f"💾 Store in DB: {metadata.get('store', True)}")
        print(f"\033[93m💬 Full Response: {ai_reply}\033[0m")
        print("="*80 + "\n")
        
        # Return structured response
        return {
            "reply": ai_reply,
            "metadata": metadata,
            "conversation_id": conversation_id,
            "analysis": {
                "message_level": msg_level,
                "category": msg_category,
                "response_time_ms": response_time_ms,
                "tokens_estimated": len(message.split()) + len(ai_reply.split()),  # Rough estimate
                "language": language,
                "user_id": user_id,
                "store": metadata.get("store", True)
            }
        }
        
    except Exception as e:
        error_time_ms = (time.time() - start_time) * 1000
        print(f"❌ Error processing chat: {e}")
        
        # Return error response in same structure
        return {
            "reply": "I'm sorry, I encountered an error processing your request. Please try again.",
            "metadata": {
                "role": "assistant",
                "sender": "assistant",
                "store": False
            },
            "conversation_id": conversation_id,
            "analysis": {
                "message_level": "critical",
                "category": "error",
                "response_time_ms": error_time_ms,
                "tokens_estimated": 0,
                "language": language,
                "user_id": user_id,
                "store": False,
                "error": str(e)
            }
        }
