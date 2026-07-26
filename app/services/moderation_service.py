import httpx
import base64
from dataclasses import dataclass
from typing import Optional
import json

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL   = "claude-sonnet-4-20250514"

MODERATION_SYSTEM_PROMPT = """
You are a content moderation system for VSSUT Vibes, a professional academic social network 
for students and alumni of Veer Surendra Sai University of Technology (VSSUT), Burla, Odisha.

Your job is to evaluate whether a post is appropriate for this platform.

FLAG the content as inappropriate if it contains ANY of the following:
- Hate speech, racism, casteism, communalism, or discrimination of any kind
- Sexual or explicit content
- Graphic violence or gore
- Bullying, harassment, or targeted personal attacks on individuals
- Dangerous or illegal activity (drugs, weapons, threats)
- Spam or scam content (fake job offers, phishing, MLM schemes)
- Severe misinformation that could harm students (fake placement results, fake exam info)
- Nudity or sexually suggestive imagery

ALLOW the content if it is:
- Academic discussion, project sharing, achievements
- Job/internship opportunities (legitimate)
- General student life, campus events, announcements
- Technical content, coding, engineering topics
- Motivational or professional content
- News or opinions shared respectfully

You MUST respond with ONLY a valid JSON object — no explanation, no markdown, no preamble:
{
  "flagged": true | false,
  "reason": "short reason if flagged, empty string if not flagged",
  "category": "hate_speech | sexual | violence | harassment | spam | misinformation | nudity | other | none"
}
""".strip()


@dataclass
class ModerationResult:
    flagged:  bool
    reason:   str
    category: str


async def _fetch_image_as_base64(url: str) -> tuple[str, str] | None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            if response.status_code != 200:
                return None
            content_type = response.headers.get("content-type", "")
            allowed = ["image/jpeg", "image/png", "image/gif", "image/webp"]
            media_type = next((m for m in allowed if m in content_type), None)
            if not media_type:
                return None
            b64 = base64.standard_b64encode(response.content).decode("utf-8")
            return b64, media_type
    except Exception:
        return None


async def moderate_content(
    text: Optional[str] = None,
    image_url: Optional[str] = None
) -> ModerationResult:
    
    content_blocks = []

    if image_url:
        image_data = await _fetch_image_as_base64(image_url)
        if image_data:
            b64, media_type = image_data
            content_blocks.append({
                "type": "image",
                "source": {
                    "type":       "base64",
                    "media_type": media_type,
                    "data":       b64
                }
            })
        else:
            content_blocks.append({
                "type": "text",
                "text": "[An image was attached but could not be retrieved for review.]"
            })

    if text:
        content_blocks.append({
            "type": "text",
            "text": f"Post text:\n{text}"
        })

    if not content_blocks:
        return ModerationResult(flagged=False, reason="", category="none")

    content_blocks.append({
        "type": "text",
        "text": "Please moderate the above post content and respond with the JSON object only."
    })

    payload = {
        "model":      CLAUDE_MODEL,
        "max_tokens": 200,
        "system":     MODERATION_SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": content_blocks}
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                CLAUDE_API_URL,
                json=payload,
                headers={"Content-Type": "application/json"}
            )

        if response.status_code != 200:
            return ModerationResult(
                flagged=False,
                reason="",
                category="none"
            )

        data = response.json()
        raw_text = data["content"][0]["text"].strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        raw_text = raw_text.strip()

        result = json.loads(raw_text)

        return ModerationResult(
            flagged=bool(result.get("flagged", False)),
            reason=result.get("reason", ""),
            category=result.get("category", "none")
        )

    except json.JSONDecodeError:
        return ModerationResult(flagged=False, reason="", category="none")

    except Exception:
        return ModerationResult(flagged=False, reason="", category="none")