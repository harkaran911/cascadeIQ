"""
Groq-powered incident text classifier — Phase 6.
Uses llama-3.1-8b-instant for zero-shot classification of citizen incident reports.

Graceful degradation: Groq failure NEVER blocks incident saving.
Classification runs async after the incident is persisted to DB.
"""
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

VALID_TYPES = {
    "flood", "road_blocked", "bridge_failure", "power_outage",
    "trapped_people", "medical_emergency", "infrastructure_damage",
}

_SYSTEM_PROMPT = """You are an emergency incident classifier for a flood disaster response system in Punjab, India (Sutlej river basin).

Classify the incident description into EXACTLY ONE of these types:
- flood              (rising water, inundation, Sutlej overflow, waterlogging)
- road_blocked       (highway/road submerged, debris blocking, vehicles stuck)
- bridge_failure     (bridge cracked, collapsed, structurally unsafe)
- power_outage       (transformer failure, lines down, no electricity)
- trapped_people     (people stranded, cut off, need rescue/evacuation)
- medical_emergency  (injuries, deaths, hospital access blocked, disease outbreak)
- infrastructure_damage (buildings collapsed, embankment breach, dam issues)

Rules:
- Respond ONLY with valid JSON — no markdown fences, no extra text
- severity: 0.0 (minor inconvenience) to 1.0 (catastrophic / life-threatening)
- confidence: your certainty about the classification (0.0 to 1.0)
- keywords: 2–3 key terms pulled directly from the description"""

_USER_TEMPLATE = """Classify this incident report from Punjab flood emergency:

"{description}"

Respond with ONLY this JSON:
{{
  "incident_type": "<type>",
  "severity": <0.0-1.0>,
  "confidence": <0.0-1.0>,
  "keywords": ["<word1>", "<word2>"],
  "reasoning": "<one sentence explaining the classification>"
}}"""


async def classify_incident(description: str) -> Optional[dict]:
    """
    Classify an incident description using Groq's llama-3.1-8b-instant.

    Returns:
        dict with keys: incident_type, severity, confidence, keywords, reasoning
        None if description is too short or Groq call fails
    """
    if not description or len(description.strip()) < 8:
        return None

    try:
        from app.core.config import settings
        api_key = getattr(settings, "GROQ_API_KEY", "demo")
        if not api_key or api_key == "demo":
            logger.warning("GROQ_API_KEY not set — skipping AI classification")
            return None

        from groq import AsyncGroq
        client = AsyncGroq(api_key=api_key)

        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": _USER_TEMPLATE.format(description=description.strip())},
            ],
            temperature=0.1,    # low temp → deterministic, consistent output
            max_tokens=256,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content.strip()
        result = json.loads(raw)

        # Sanitize
        inc_type = result.get("incident_type")
        if inc_type not in VALID_TYPES:
            logger.warning(f"Groq returned unrecognised type '{inc_type}' — discarding type")
            inc_type = None

        return {
            "incident_type": inc_type,
            "severity":      max(0.0, min(1.0, float(result.get("severity",   0.5)))),
            "confidence":    max(0.0, min(1.0, float(result.get("confidence", 0.0)))),
            "keywords":      result.get("keywords", [])[:4],   # cap at 4
            "reasoning":     str(result.get("reasoning", ""))[:300],
        }

    except json.JSONDecodeError as e:
        logger.warning(f"Groq returned non-JSON: {e}")
        return None
    except Exception as e:
        logger.warning(f"Groq classification error: {e}")
        return None
