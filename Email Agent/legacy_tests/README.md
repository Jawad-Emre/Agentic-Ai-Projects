# Legacy Test Scripts

These are early, ad-hoc test scripts used during initial development to verify
each component against real Gmail/Supabase/Gemini APIs (live calls, not mocked).
They're preserved here for reference showing the incremental build process.

Current test coverage lives in `tests/test_agent_logic.py`, using proper mocked
unit tests instead of live API calls.