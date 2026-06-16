import threading

class AssistantState:
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"
    FOLLOW_UP = "FOLLOW_UP"
    INTERRUPTED = "INTERRUPTED"

_current_state = AssistantState.IDLE
_state_lock = threading.Lock()
_follow_up_start_time = 0.0

def get_state():
    global _current_state
    with _state_lock:
        return _current_state

def set_state(new_state):
    global _current_state, _follow_up_start_time
    with _state_lock:
        old_state = _current_state
        _current_state = new_state
        print(f"[STATE MACHINE] {old_state} -> {new_state}")
        
        # Logging requirements
        if new_state == AssistantState.FOLLOW_UP:
            import time
            _follow_up_start_time = time.time()
            print("[VOICE UX] Follow-up mode entered")
        elif old_state == AssistantState.FOLLOW_UP and new_state == AssistantState.IDLE:
            print("[VOICE UX] Follow-up timeout")
        elif new_state == AssistantState.INTERRUPTED:
            print("[VOICE UX] Interrupt detected")
            
    # Emit to GUI
    try:
        from ui.window import signals
        signals.status_changed.emit(new_state)
    except Exception as e:
        pass

def get_follow_up_start_time():
    global _follow_up_start_time
    with _state_lock:
        return _follow_up_start_time

def reset_follow_up_timer():
    global _follow_up_start_time
    import time
    with _state_lock:
        _follow_up_start_time = time.time()
        print("[VOICE UX] Follow-up timer reset")
