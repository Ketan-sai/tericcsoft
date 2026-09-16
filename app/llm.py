import json
from typing import List, Dict, Any
from groq import Groq, APIConnectionError, RateLimitError, AuthenticationError, APIStatusError
from app.config import GROQ_API_KEY, GROQ_MODEL
from app.schemas import LLMLeadAnalysis

class LLMServiceError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

SYSTEM_PROMPT = (
    "You are a B2B sales qualification analyst for Nimbus Software. You analyze inbound "
    "customer requirements and produce structured qualification notes for the sales team.\n"
    "RULES: Only reference products that appear in the PRODUCT CONTEXT provided. Never invent "
    "products, pricing, or features. If the context is a weak match, say so in the summary.\n"
    "Respond with a single valid JSON object and nothing else."
)

SCHEMA_INSTRUCTION = """
Required JSON schema:
{
  "lead_summary": "string, 2-3 sentences",
  "relevant_products": [{"name": "string", "why": "string"}],
  "customer_needs": ["string", ...],
  "recommended_next_step": "string",
  "follow_up_questions": ["string", "string", "string"],
  "lead_score": 0-100,
  "priority": "High" | "Medium" | "Low"
}
"""

def check_groq_api_key():
    if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
        raise LLMServiceError(
            "GROQ_API_KEY is not configured. Please add a valid GROQ_API_KEY in your .env file.",
            status_code=500
        )

def get_groq_client() -> Groq:
    check_groq_api_key()
    return Groq(api_key=GROQ_API_KEY)

def format_user_prompt(requirement: str, kb_entries: List[Dict[str, Any]]) -> str:
    kb_blocks = []
    for i, entry in enumerate(kb_entries, 1):
        features_str = ", ".join(entry.get("features", []))
        block = (
            f"Product {i}:\n"
            f"- Name: {entry.get('name')}\n"
            f"- Category: {entry.get('category')}\n"
            f"- Description: {entry.get('description')}\n"
            f"- Features: {features_str}"
        )
        kb_blocks.append(block)

    formatted_kb = "\n\n".join(kb_blocks)

    return (
        f"CUSTOMER REQUIREMENT:\n{requirement}\n\n"
        f"PRODUCT CONTEXT:\n{formatted_kb}\n\n"
        f"OUTPUT SCHEMA:\n{SCHEMA_INSTRUCTION}"
    )

_cached_active_model = ""

def get_active_model(client: Groq) -> str:
    global _cached_active_model
    if _cached_active_model:
        return _cached_active_model

    requested = GROQ_MODEL or "openai/gpt-oss-120b"
    try:
        available = [m.id for m in client.models.list().data]
        if requested in available:
            _cached_active_model = requested
            return requested

        preferred_order = [
            "llama-3.3-70b-versatile",
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "qwen/qwen3.8-27b",
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant"
        ]
        for candidate in preferred_order:
            if candidate in available:
                _cached_active_model = candidate
                return candidate

        for m_id in available:
            if not m_id.startswith("whisper") and "prompt-guard" not in m_id:
                _cached_active_model = m_id
                return m_id
    except Exception:
        pass

    _cached_active_model = requested
    return requested

def analyze_lead_with_groq(requirement: str, kb_entries: List[Dict[str, Any]]) -> LLMLeadAnalysis:
    check_groq_api_key()
    try:
        client = get_groq_client()
    except LLMServiceError:
        raise
    except Exception as e:
        raise LLMServiceError(f"Failed to initialize Groq client: {str(e)}", status_code=500)

    active_model = get_active_model(client)

    user_content = format_user_prompt(requirement, kb_entries)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content}
    ]

    last_error_msg = ""

    for attempt in range(2):
        raw_text = ""
        try:
            response = client.chat.completions.create(
                model=active_model,
                temperature=0.3,
                max_tokens=1200,
                response_format={"type": "json_object"},
                messages=messages
            )
            raw_text = response.choices[0].message.content or ""
            if not raw_text.strip():
                raise ValueError("Groq returned an empty response.")

            parsed = json.loads(raw_text)
            validated = LLMLeadAnalysis.model_validate(parsed)
            return validated
        except (AuthenticationError, RateLimitError, APIConnectionError, APIStatusError) as api_err:
            error_message = getattr(api_err, "message", str(api_err))
            raise LLMServiceError(f"Groq API communication error: {error_message}", status_code=502)
        except Exception as validation_err:
            last_error_msg = str(validation_err)
            if attempt == 0:
                messages.append({
                    "role": "assistant",
                    "content": raw_text if raw_text else "{}"
                })
                messages.append({
                    "role": "user",
                    "content": (
                        f"The previous output failed validation: {last_error_msg}. "
                        "Please correct any schema or JSON issues and return a single valid JSON object strictly matching the required schema."
                    )
                })
            else:
                break

    raise LLMServiceError(
        f"Failed to parse and validate qualification notes from Groq LLM: {last_error_msg}",
        status_code=502
    )
