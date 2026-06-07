import re
import difflib

class FollowUpValidationService:
    # Phrases typically found in video/audio background noise
    BACKGROUND_PHRASES = [
        "thanks for watching",
        "thank you for watching",
        "like and subscribe",
        "subscribe to my channel",
        "hey everyone",
        "welcome back",
        "welcome back to my channel",
        "see you next time",
        "see you in the next video",
        "see you in the next one",
        "hit the bell icon",
        "leave a comment",
        "hope you enjoyed"
    ]
    
    # Common command or follow-up indicators
    GENUINE_INDICATORS = [
        r"\bchange it to\b",
        r"\bopen it\b",
        r"\bcontinue\b",
        r"\bgo ahead\b",
        r"\byes\b",
        r"\bno\b",
        r"\bcursor\b",
        r"\bvs code\b",
        r"\bopen\b",
        r"\brun\b",
        r"\bdelete\b",
        r"\bclear\b",
        r"\bshow\b",
        r"\bwhat is\b",
        r"\bwhat's\b",
        r"\bfind\b",
        r"\bgenerate\b",
        r"\bcheck\b",
        r"\btest\b",
        r"\bcreate\b",
        r"\bmake\b",
        r"\bbuild\b",
        r"\bwrite\b",
        r"\bprint\b",
        r"\badd\b",
        r"\bremove\b",
        r"\bget\b",
        r"\buse\b",
        r"\blist\b",
        r"\btell\b"
    ]

    @classmethod
    def calculate_confidence(cls, text: str) -> float:
        """Calculates a confidence score between 0.0 and 1.0 that this is a genuine command."""
        text_clean = text.lower().strip()
        if not text_clean:
            return 0.0

        # Check direct background phrase match
        for phrase in cls.BACKGROUND_PHRASES:
            # Full match or very high similarity
            if phrase in text_clean:
                print(f"[Background Speech Detected] query='{text_clean}' matched phrase='{phrase}'")
                return 0.0
            
            # Fuzzy match check for transcription variations
            ratio = difflib.SequenceMatcher(None, text_clean, phrase).ratio()
            if ratio >= 0.8:
                print(f"[Background Speech Detected] query='{text_clean}' fuzzy matched phrase='{phrase}' ratio={ratio:.2f}")
                return 0.0

        # Check genuine indicators
        for pattern in cls.GENUINE_INDICATORS:
            if re.search(pattern, text_clean):
                return 1.0

        # Base confidence depending on length and typical action verbs
        words = text_clean.split()
        if len(words) <= 3:
            # Short statements might be follow-ups ("yes", "ok", "open VS Code") or noise.
            # If no genuine indicators matched, give a medium-low confidence
            return 0.4
        
        # Default fallback confidence
        return 0.7

    @classmethod
    def check_relevance(cls, text: str, previous_command: str, previous_response: str) -> bool:
        """Determines if the command is contextually relevant to the previous turn."""
        text_clean = text.lower().strip()
        prev_cmd_clean = previous_command.lower().strip() if previous_command else ""
        prev_resp_clean = previous_response.lower().strip() if previous_response else ""

        # Standalone clean commands (not using relative pronouns) are always considered relevant
        relative_pronouns = [r"\bit\b", r"\bthat\b", r"\bthis\b", r"\bthem\b", r"\bhim\b", r"\bher\b"]
        has_relative = any(re.search(pat, text_clean) for pat in relative_pronouns)
        
        if not has_relative:
            return True

        # If it has relative pronouns, check if previous context contains target entities
        # E.g. "What is my preferred editor?" -> "VS Code" / "editor"
        # "Change it to Cursor" -> "it" refers to editor / VS Code.
        target_nouns = ["editor", "ide", "language", "app", "path", "name", "greeting", "voice", "volume"]
        
        # Check if previous context mentions a target noun
        context_words = prev_cmd_clean.split() + prev_resp_clean.split()
        for noun in target_nouns:
            if noun in context_words:
                return True

        # Check if previous response had actual preference values
        pref_indicators = ["vs code", "cursor", "python", "java", "spring boot", "c#", "c++"]
        for ind in pref_indicators:
            if ind in prev_resp_clean or ind in prev_cmd_clean:
                return True

        return False

    @classmethod
    def validate_follow_up(cls, text: str, previous_command: str = "", previous_response: str = "", is_active_window: bool = False) -> tuple[bool, float]:
        """Main entry point to validate if a follow-up statement is safe and genuine."""
        text_clean = text.lower().strip()
        
        if is_active_window:
            print(f"[Active Window Triggered] query='{text_clean}'")
            
        print(f"[Follow-Up Validation] Checking command: '{text_clean}'")
        
        confidence = cls.calculate_confidence(text_clean)
        print(f"[Confidence Score] score={confidence:.2f}")

        if confidence < 0.5:
            print("[Command Rejected] Reason: Low confidence background speech.")
            return False, confidence

        if is_active_window and previous_command:
            is_relevant = cls.check_relevance(text_clean, previous_command, previous_response)
            if not is_relevant:
                print("[Command Rejected] Reason: Unrelated follow-up in active window.")
                return False, confidence

        print("[Command Accepted]")
        return True, confidence

    @classmethod
    def verify_tool_execution(cls, text: str, intent_confidence: float = 1.0) -> bool:
        """Verifies safety confidence before executing any tools."""
        text_clean = text.lower().strip()
        confidence = cls.calculate_confidence(text_clean)
        
        if confidence < 0.5 or intent_confidence < 0.5:
            print("[Tool Execution Blocked] Reason: Low command or intent confidence.")
            return False
            
        return True
