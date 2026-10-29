# Pace testing log

## 28 October 2026: AI backup with no API key
- Test: commented out ANTHROPIC_API_KEY in .env, restarted, added "Go to work"
- Expected: "AI was not available" message with keyword steps
- Actual: page crashed with TypeError (no key is a different error from a wrong key)
- Fix: suggest_task now checks for a missing key and catches any unexpected error
- Retest: passed with no key and with a valid key