# Plan: Goal Memory Pipeline Fix

## Overview
Fix the Goal Memory pipeline where natural language goal statements (e.g., "I want to become a backend developer") fall through to the ReAct agent executor instead of being extracted and saved directly.

## Success Criteria
- Querying "I want to become a backend developer" extracts and creates the goal.
- Querying "What are my goals?" lists the new goal.
- Restarting the application preserves the goals in the database.

## Tasks
- [x] Task 1: Modify `handle_goal_intents` in `agent.py` to route general goal statements to `process_natural_language_goal`.
- [x] Task 2: Validate the fix using custom test scenarios.
- [x] Task 3: Run full pytest suite to ensure no regressions.

## ✅ PHASE X COMPLETE
- Lint: ✅ Pass
- Security: ✅ No critical issues
- Build: ✅ Success
- Date: 2026-06-17
