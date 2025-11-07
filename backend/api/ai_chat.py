"""
AI Chat API Endpoint
Handles chat conversations with AI models (OpenAI/Anthropic)
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import os
from datetime import datetime
import httpx
import json
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet

from database import get_db, Settings

router = APIRouter()

# Encryption key for decrypting API keys from database
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
cipher_suite = Fernet(ENCRYPTION_KEY.encode())


class Message(BaseModel):
    """Chat message model"""

    role: str = Field(..., description="Role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat request model"""

    messages: List[Message] = Field(..., description="Conversation history")
    model: Optional[str] = Field(None, description="AI model to use")
    temperature: Optional[float] = Field(0.7, ge=0, le=2, description="Sampling temperature")
    max_tokens: Optional[int] = Field(1000, ge=1, le=4000, description="Maximum tokens to generate")
    stream: Optional[bool] = Field(False, description="Stream response")


class ChatResponse(BaseModel):
    """Chat response model"""

    message: Message
    model: str
    created_at: str
    usage: Optional[Dict[str, int]] = None


def get_setting_value(db: Session, key: str) -> Optional[str]:
    """Get a decrypted setting value from database"""
    setting = db.query(Settings).filter(Settings.key == key).first()
    if not setting:
        return None

    value = setting.value
    if setting.encrypted:
        try:
            value = cipher_suite.decrypt(value.encode()).decode()
        except:
            return None

    return value


def get_ai_provider(db: Session):
    """Determine which AI provider to use based on available API keys in database"""
    # Check database first (primary source)
    openai_key = get_setting_value(db, "openai_api_key")
    anthropic_key = get_setting_value(db, "anthropic_api_key")

    # Fallback to environment variables
    if not openai_key:
        openai_key = os.getenv("OPENAI_API_KEY")
    if not anthropic_key:
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if openai_key:
        return "openai", openai_key
    elif anthropic_key:
        return "anthropic", anthropic_key
    else:
        raise HTTPException(
            status_code=500,
            detail="No AI API key configured. Please add your OpenAI or Anthropic API key in your Profile settings.",
        )


async def call_openai(
    messages: List[Message], model: str, temperature: float, max_tokens: int, api_key: str
) -> Dict[str, Any]:
    """Call OpenAI API"""

    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    payload = {
        "model": model or "gpt-3.5-turbo",
        "messages": [{"role": msg.role, "content": msg.content} for msg in messages],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="AI API request timed out")
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code, detail=f"AI API error: {e.response.text}"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI API error: {str(e)}")


async def call_anthropic(
    messages: List[Message], model: str, temperature: float, max_tokens: int, api_key: str
) -> Dict[str, Any]:
    """Call Anthropic API"""

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }

    # Convert messages to Anthropic format
    system_message = next((msg.content for msg in messages if msg.role == "system"), None)
    user_messages = [
        {"role": msg.role, "content": msg.content} for msg in messages if msg.role != "system"
    ]

    payload = {
        "model": model or "claude-3-sonnet-20240229",
        "messages": user_messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if system_message:
        payload["system"] = system_message

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            # Convert Anthropic response to OpenAI-like format
            return {
                "choices": [
                    {"message": {"role": "assistant", "content": data["content"][0]["text"]}}
                ],
                "model": data["model"],
                "usage": {
                    "prompt_tokens": data["usage"]["input_tokens"],
                    "completion_tokens": data["usage"]["output_tokens"],
                    "total_tokens": data["usage"]["input_tokens"] + data["usage"]["output_tokens"],
                },
            }
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="AI API request timed out")
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code, detail=f"AI API error: {e.response.text}"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI API error: {str(e)}")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Send a chat message to AI and get a response

    Supports both OpenAI and Anthropic models based on configured API keys
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages list cannot be empty")

    try:
        # Determine provider and get API key
        provider, api_key = get_ai_provider(db)

        # Call appropriate API
        if provider == "openai":
            result = await call_openai(
                request.messages, request.model, request.temperature, request.max_tokens, api_key
            )
        else:  # anthropic
            result = await call_anthropic(
                request.messages, request.model, request.temperature, request.max_tokens, api_key
            )

        # Extract response
        assistant_message = result["choices"][0]["message"]

        return ChatResponse(
            message=Message(role=assistant_message["role"], content=assistant_message["content"]),
            model=result.get("model", request.model or "unknown"),
            created_at=datetime.utcnow().isoformat(),
            usage=result.get("usage"),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@router.get("/models")
async def list_models(db: Session = Depends(get_db)):
    """List available AI models"""
    provider, _ = get_ai_provider(db)

    if provider == "openai":
        return {
            "provider": "openai",
            "models": ["gpt-4", "gpt-4-turbo-preview", "gpt-3.5-turbo", "gpt-3.5-turbo-16k"],
        }
    else:
        return {
            "provider": "anthropic",
            "models": [
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
            ],
        }


@router.get("/health")
async def health(db: Session = Depends(get_db)):
    """Check if AI chat service is healthy"""
    try:
        provider, api_key = get_ai_provider(db)
        return {"status": "healthy", "provider": provider, "api_key_configured": bool(api_key)}
    except HTTPException as e:
        return {"status": "unhealthy", "error": e.detail}
