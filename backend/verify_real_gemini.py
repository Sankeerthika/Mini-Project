import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.meeting_analysis_service import get_meeting_analysis_service

SHORT_TRANSCRIPT = (
    "Sara: Good morning everyone. Let's start the weekly sync. First, we need to finalize the new feature release date. "
    "I propose we launch on November 15th 2026. All in favor? "
    "Mark: Agreed. Launch date is November 15th 2026. "
    "Sara: Great. Mark, please prepare the release notes document by Friday this week. "
    "Linda: I will set up the marketing campaign landing page by next Monday. "
    "Sara: And I need each of you to review the QA test plan and send feedback by tomorrow end of day. "
    "Key decision: The team agreed the launch date is 2026-11-15 instead of the prior mid-October target."
)

DEADLINE_RE = r"\d{4}-\d{2}-\d{2}"

def safe_check(text, field_name):
    if not isinstance(text, str) or not text.strip():
        return False, f"{field_name} is empty or not string"
    # Must be real, not mock
    if "[MOCK]" in text:
        return False, f"{field_name} contains [MOCK] prefix — mock response used"
    return True, "ok"

def main():
    print("=" * 60)
    print("REAL GEMINI VERIFICATION")
    print("=" * 60)

    # Force fresh service so env is reloaded from .env changes
    import app.services.meeting_analysis_service as mas
    mas._default_analysis_service = None
    from app.services.meeting_analysis_service import MeetingAnalysisService
    service = MeetingAnalysisService()

    print(f"[INFO] SDK package: google-generativeai installed = {service._genai is not None}")
    print(f"[INFO] is_using_mock = {service.is_using_mock}")
    print(f"[INFO] model_name = {service.model_name}")
    print(f"[INFO] api_key present (value hidden) = {bool(service.api_key and service.api_key.strip())}")

    if service.is_using_mock:
        print("\n[RESULT] REAL GEMINI CALL: NOT VERIFIED")
        print("         Reason: Service reports is_using_mock = True (SDK missing, API key empty/placeholder, or init exception)")
        sys.exit(1)

    # Actually call Gemini
    print("\n[INFO] Calling analyze_transcript() with short sample transcript...")
    try:
        result = service.analyze_transcript(SHORT_TRANSCRIPT)
    except Exception as e:
        print(f"\n[RESULT] REAL GEMINI CALL: NOT VERIFIED")
        print(f"         Exception during generate_content: {type(e).__name__}: {e}")
        sys.exit(2)

    # Validate structure
    print("[INFO] Response received. Validating structure...")
    errors = []

    if not isinstance(result, dict):
        errors.append(f"result is not a dict (got {type(result).__name__})")

    summary = (result or {}).get("meeting_summary")
    decisions = (result or {}).get("key_decisions")
    actions = (result or {}).get("action_items")

    ok, msg = safe_check(summary, "meeting_summary")
    if not ok: errors.append(msg)
    print(f"  meeting_summary non-empty + no [MOCK] = {ok}")

    if not isinstance(decisions, list):
        errors.append(f"key_decisions is not a list (got {type(decisions).__name__})")
    elif len(decisions) == 0:
        errors.append("key_decisions list is empty")
    else:
        # Any decision contains [MOCK]?
        bad = [d for d in decisions if isinstance(d, str) and "[MOCK]" in d]
        if bad:
            errors.append(f"key_decisions has [MOCK] entries: {bad}")
    print(f"  key_decisions list non-empty + no [MOCK] = {isinstance(decisions, list) and len(decisions) > 0 and not any(isinstance(d,str) and '[MOCK]' in d for d in decisions)}")

    if not isinstance(actions, list):
        errors.append(f"action_items is not a list (got {type(actions).__name__})")
    elif len(actions) == 0:
        errors.append("action_items list is empty")
    else:
        for i, it in enumerate(actions):
            if not isinstance(it, dict):
                errors.append(f"action_items[{i}] not dict: {type(it).__name__}")
                continue
            task = it.get("task")
            if not isinstance(task, str) or not task.strip():
                errors.append(f"action_items[{i}] missing non-empty task")
            if isinstance(task, str) and "[MOCK]" in task:
                errors.append(f"action_items[{i}] task has [MOCK] prefix")
            if "person" not in it:
                errors.append(f"action_items[{i}] missing 'person' key")
            if "deadline" not in it:
                errors.append(f"action_items[{i}] missing 'deadline' key")
            person = it.get("person")
            if person is not None and not isinstance(person, str):
                errors.append(f"action_items[{i}] person must be string or null")
            deadline = it.get("deadline")
            if deadline is not None and (not isinstance(deadline, str) or not re_match_date(deadline)):
                errors.append(f"action_items[{i}] deadline must be null or YYYY-MM-DD string")
    print(f"  action_items list non-empty + each dict has task/person/deadline shape = {isinstance(actions, list) and len(actions) > 0}")

    print("\n--- Raw response (keys only + lengths) ---")
    print(f"  meeting_summary: len={len(summary) if isinstance(summary, str) else 'N/A'}")
    print(f"  key_decisions: count={len(decisions) if isinstance(decisions, list) else 'N/A'}")
    print(f"  action_items: count={len(actions) if isinstance(actions, list) else 'N/A'}")

    # Print first action item for inspection (no [MOCK])
    if isinstance(actions, list) and actions:
        first = actions[0]
        if isinstance(first, dict):
            print(f"\nSample first action item = {json.dumps(first, ensure_ascii=False)}")

    if errors:
        print("\n[RESULT] REAL GEMINI CALL: NOT VERIFIED")
        print("Issues found:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(3)

    print("\n" + ("=" * 60))
    print("[RESULT] REAL GEMINI CALL: PASS")
    print("  ✓ Real google.generativeai SDK loaded (is_using_mock=False)")
    print("  ✓ meeting_summary populated and non-[MOCK]")
    print("  ✓ key_decisions populated list and non-[MOCK]")
    print("  ✓ action_items populated list and each item shaped {task, person, deadline} with no [MOCK]")
    print("=" * 60)


def re_match_date(s: str) -> bool:
    import re
    return bool(re.fullmatch(DEADLINE_RE, s))


if __name__ == "__main__":
    main()
