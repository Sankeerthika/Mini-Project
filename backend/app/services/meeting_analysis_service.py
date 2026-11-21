import os
import json
import re
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()


_DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


class MeetingAnalysisService:
    def __init__(self, model_name: str | None = None):
        self.api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
        self.model_name = model_name or os.getenv("GOOGLE_GEMINI_MODEL", _DEFAULT_GEMINI_MODEL)
        self.model = None
        self._genai = None
        self._initialize_client()

    def _initialize_client(self):
        try:
            import google.generativeai as genai
            self._genai = genai
            if self.api_key and self.api_key.strip() and "your_gemini" not in self.api_key:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.model_name)
                print(f"[MeetingAnalysisService] Gemini client initialized (model={self.model_name})")
            else:
                print("[MeetingAnalysisService] GOOGLE_GEMINI_API_KEY not set or is placeholder. Using mock fallback.")
        except ImportError:
            print("[MeetingAnalysisService] google-generativeai package not installed. Using mock fallback.")
        except Exception as e:
            print(f"[MeetingAnalysisService] Failed to initialize Gemini client: {e}. Using mock fallback.")
            self.model = None
            self._genai = None

    @property
    def is_using_mock(self) -> bool:
        return self.model is None

    def analyze_transcript(self, transcript: str) -> Dict[str, Any]:
        if not self.model:
            return self._get_mock_analysis(transcript)

        prompt = f"""You are a meeting analysis assistant. Analyze ONLY the meeting transcript provided below. Do not use any external knowledge.

Strict rules:
- Generate a concise, factual meeting_summary (2-3 sentences). Do not embellish.
- key_decisions: Array of strings. Include ONLY decisions that were EXPLICITLY stated or agreed upon. If none, return [].
- action_items: Array of objects. Include ONLY tasks that were EXPLICITLY assigned as next steps. If none, return [].
- For each action item:
  - "task": Exact task described. Short string. Required.
  - "person": The person EXPLICITLY named as responsible. If not clearly assigned to a named person, use null. Do NOT invent names. Do NOT infer roles unless explicitly stated.
  - "deadline": Date in YYYY-MM-DD format. Include ONLY if the transcript explicitly mentions a date (e.g. "by October 10th"). If no explicit date, use null. Do NOT invent or estimate dates from vague phrases like "sometime next week" or "later".

Do not invent tasks, decisions, people, or deadlines. If uncertain about a field, use null or empty array.

Return ONLY valid JSON matching this schema exactly:
{{
  "meeting_summary": string,
  "key_decisions": [string, ...],
  "action_items": [
    {{
      "task": string,
      "person": string | null,
      "deadline": string | null
    }}
  ]
}}

Meeting Transcript:
{transcript}
"""

        try:
            response = self.model.generate_content(prompt)
            result = self._parse_response(response.text)
            return self._normalize_result(result)
        except Exception as e:
            print(f"[MeetingAnalysisService] Gemini analysis failed: {e}")
            return self._get_mock_analysis(transcript)

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        cleaned = response_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        match = re.search(r'\{[\s\S]*\}', cleaned)
        if match:
            cleaned = match.group(0)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"[MeetingAnalysisService] JSON parse error: {e}")
            return self._get_mock_analysis("")

    def _normalize_result(self, data: Any) -> Dict[str, Any]:
        if not isinstance(data, dict):
            return self._get_mock_analysis("")

        summary = data.get("meeting_summary") or ""
        if not isinstance(summary, str):
            summary = ""

        decisions = data.get("key_decisions") or []
        if not isinstance(decisions, list):
            decisions = []
        decisions = [str(d) for d in decisions if d is not None]

        items = data.get("action_items") or []
        if not isinstance(items, list):
            items = []
        normalized_items = []
        for raw in items:
            if not isinstance(raw, dict):
                continue
            task = raw.get("task") or raw.get("title") or ""
            if not isinstance(task, str) or not task.strip():
                continue
            person = raw.get("person") or raw.get("assigned_person")
            if isinstance(person, str):
                person = person.strip() or None
            else:
                person = None
            deadline = raw.get("deadline")
            if isinstance(deadline, str):
                deadline = deadline.strip()
                if not deadline or deadline.lower() in {"", "tbd", "n/a", "none"}:
                    deadline = None
                else:
                    m = re.match(r'(\d{4}-\d{2}-\d{2})', deadline)
                    if not m:
                        deadline = None
                    else:
                        deadline = m.group(1)
            else:
                deadline = None
            normalized_items.append({
                "task": task.strip(),
                "person": person,
                "deadline": deadline,
            })

        return {
            "meeting_summary": summary.strip(),
            "key_decisions": decisions,
            "action_items": normalized_items,
        }

    def _get_mock_analysis(self, transcript: str) -> Dict[str, Any]:
        return {
            "meeting_summary": "[MOCK] This is a placeholder summary. Set a valid GOOGLE_GEMINI_API_KEY to enable real Gemini analysis.",
            "key_decisions": [
                "[MOCK] Connect a valid GOOGLE_GEMINI_API_KEY to extract real key decisions from the transcript."
            ],
            "action_items": [
                {
                    "task": "[MOCK] Connect a valid GOOGLE_GEMINI_API_KEY to extract real action items.",
                    "person": None,
                    "deadline": None,
                }
            ]
        }


_default_analysis_service: MeetingAnalysisService | None = None


def get_meeting_analysis_service() -> MeetingAnalysisService:
    global _default_analysis_service
    if _default_analysis_service is None:
        _default_analysis_service = MeetingAnalysisService()
    return _default_analysis_service
