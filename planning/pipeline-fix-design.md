# Pipeline Fix Design Document

This document outlines the proposed changes to correct the wake-word false triggers, Whisper transcription errors, and heuristic intent classification errors.

---

## 🛠️ 1. Proposed Code Modifications

### A. Increase Fuzzy Matching Threshold ([listener.py](file:///c:/Users/SHAN%20KUMAR/Desktop/ALONE/alone/core/listener.py))
- **Modification**: Change the default similarity threshold in `match_wake_word_fuzzy(normalized_text, threshold=0.75)` to `0.85`.
- **Rationale**:
  - A threshold of `0.85` restricts matches to at most **1 edit distance** on targets `"hey alone"` (9 chars) and `"ok alone"` (8 chars).
  - Any edit distance $\ge 2$ yields a similarity score of $\le 0.778$, thereby preventing `"you alone"` (similarity 0.778) and `"be alone"` (similarity 0.778) from false-triggering the system.
  - Authentic phonetic matches listed in `two_word_phonetic_triggers` will continue to pass as their hardcoded similarity is `0.98`.

### B. Guide Whisper with `initial_prompt` ([transcriber.py](file:///c:/Users/SHAN%20KUMAR/Desktop/ALONE/alone/core/transcriber.py))
- **Modification**: Pass `initial_prompt="Hey Alone, ok alone."` to `model.transcribe()` in both the class method `Transcriber.transcribe` and the global `transcribe` function.
- **Rationale**: Biases Whisper's transcription toward correctly recognizing the phrase `"Hey Alone"` or `"ok alone"` rather than phonetically approximating them to `"hello"`, `"you alone"`, or `"be alone"`.

### C. Refine `USER_PROFILE_UPDATE` Regex Heuristics ([agent.py](file:///c:/Users/SHAN%20KUMAR/Desktop/ALONE/alone/core/agent.py))
- **Modification**:
  - Remove the highly generic prefix patterns `r"^i\s+am\s+"` and `r"^i'm\s+"` from `heuristics_classify`.
  - Add specific, safe alternatives such as:
    ```python
    r"^i\s+am\s+(?:a\s+|an\s+)?(?:developer|engineer|programmer|designer|student|teacher|architect|user)"
    ```
- **Rationale**: Prevents general tool execution instructions (e.g. `"I am going to check my files"`) from being misclassified as `USER_PROFILE_UPDATE` intents.

### D. Correct Callback Parameters in Listener Fallback Loop ([listener.py](file:///c:/Users/SHAN%20KUMAR/Desktop/ALONE/alone/core/listener.py))
- **Modification**: In `listener.py` VAD fallback one-shot command detection, change `callback(audio_path)` to `callback(audio_path, wake_word_detected=True)`.
- **Rationale**: Ensures `main.py` is informed that the wake word was already checked and matched, avoiding a redundant fuzzy match scan on the normalized text.

---

## 🔍 2. Pipeline Diagnostics Mode

We will integrate structured console logging prefixed with `[PIPELINE DIAGNOSTIC]` at each stage in [main.py](file:///c:/Users/SHAN%20KUMAR/Desktop/ALONE/alone/main.py) and [listener.py](file:///c:/Users/SHAN%20KUMAR/Desktop/ALONE/alone/core/listener.py) to trace raw audio files through to completion without modifying the user HUD interface:

```
[PIPELINE DIAGNOSTIC] Raw audio file received: {audio_path}
[PIPELINE DIAGNOSTIC] Whisper transcription: "{text}"
[PIPELINE DIAGNOSTIC] Fuzzy wake-word check: detected={detected}, matched={matched_phrase}, sim={confidence:.2f}
[PIPELINE DIAGNOSTIC] Listening window check: is_active_window={is_active_window}
[PIPELINE DIAGNOSTIC] Command extraction result: "{clean_text}"
[PIPELINE DIAGNOSTIC] Intent Router determination: intent={intent}
```

---

## 🧪 3. Verification & Regression Plan

We will create a new test file **[test_speech_regression.py](file:///c:/Users/SHAN%20KUMAR/Desktop/ALONE/alone/tests/test_speech_regression.py)** verifying these criteria:

1. **Verify False-Positive Rejections**:
   - Assert `"you alone"` and `"be alone"` are not matched as wake words.
2. **Verify Correct Wake Word and Stripping**:
   - Assert `"hey alone my name is subrato"` detects the wake word and extracts `"my name is subrato"`.
3. **Verify Intent Classification for identity and tools**:
   - Assert `"my name is subrato"` classifies as `USER_PROFILE_UPDATE`.
   - Assert `"i am going to open a file"` does **not** classify as `USER_PROFILE_UPDATE`.
4. **Ensure No Test Regressions**:
   - Run the full pytest suite to verify all 65 tests remain passing.
