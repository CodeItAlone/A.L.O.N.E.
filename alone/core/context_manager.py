import os
import time
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    # A standard rule of thumb: ~4 characters per token or ~1.3 tokens per word
    words = text.split()
    return max(len(text) // 4, int(len(words) * 1.33))

def estimate_messages_tokens(messages: list) -> int:
    total = 0
    for m in messages:
        total += estimate_tokens(m.content)
        total += 4  # Message wrapper overhead
    return total

class ContextManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ContextManager, cls).__new__(cls, *args, **kwargs)
            cls._instance._init_manager()
        return cls._instance

    def _init_manager(self):
        self.summarization_events = []
        self.retrieval_queries_count = 0
        self.total_memories_retrieved = 0
        self.last_query_estimated_context_size = 0
        self.last_query_token_usage = 0

    def clean_message_content(self, content: str) -> str:
        """Requirement 3: Never include raw logs or debug traces in prompts."""
        if not content:
            return ""
        lines = content.splitlines()
        filtered_lines = [
            line for line in lines
            if not (
                "[DEBUG LOGGING]" in line or
                "[PIPELINE DIAGNOSTIC]" in line or
                "[Preference Intent Detected]" in line or
                "[Memory Warning]" in line or
                "Task id " in line or
                "finished with result:" in line
            )
        ]
        return "\n".join(filtered_lines)

    def log_retrieval(self, query: str, num_retrieved: int):
        self.retrieval_queries_count += 1
        self.total_memories_retrieved += num_retrieved

    def summarize_and_trim(self, llm, history_list: list) -> tuple[list, str]:
        """Requirement 4: When conversation exceeds 10,000 tokens:
           - Generate a concise summary.
           - Store the summary in memory.
           - Remove old messages from active context."""
        total_tokens = estimate_messages_tokens(history_list)
        if total_tokens <= 10000:
            return history_list, ""

        print(f"[ContextManager] History is {total_tokens} tokens, exceeding the 10,000 limit. Generating summary...")

        # Keep the last 4 messages to preserve immediate continuity
        keep_count = min(4, len(history_list))
        messages_to_summarize = history_list[:-keep_count] if keep_count > 0 else history_list
        messages_to_keep = history_list[-keep_count:] if keep_count > 0 else []

        summary_prompt = (
            "Summarize the key points, user details, and decisions of the following conversation history concisely "
            "so it can be used as context. Be extremely concise:\n\n"
        )
        for msg in messages_to_summarize:
            role = "User" if isinstance(msg, HumanMessage) else "Assistant"
            summary_prompt += f"{role}: {msg.content}\n"

        summary_msg = [HumanMessage(content=summary_prompt)]
        
        try:
            response = llm.invoke(summary_msg)
            summary_text = response.content.strip()
        except Exception as e:
            print(f"[ContextManager Warning] Summarization failed: {e}")
            summary_text = f"Conversation summary up to {time.strftime('%Y-%m-%d %H:%M:%S')} due to context limits."

        # Store the summary in persistent ChromaDB memory
        try:
            from core import memory
            memory.add_memory(
                role="system",
                content=f"Summary of previous conversation: {summary_text}",
                metadata={"type": "context_summary", "timestamp": time.time()}
            )
        except Exception as e:
            print(f"[ContextManager Warning] Failed to store summary in memory: {e}")

        self.summarization_events.append({
            "timestamp": time.time(),
            "time_str": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": summary_text,
            "saved_tokens": total_tokens - estimate_messages_tokens(messages_to_keep)
        })

        return messages_to_keep, summary_text

    def enforce_limits_and_warn(self, history_list: list, system_prompt: str) -> list:
        """Requirement 1: Hard cap active context to 16,384 tokens.
           Requirement 7: Add token usage monitoring and warnings when context exceeds 80% of limit."""
        clean_sys_prompt = self.clean_message_content(system_prompt)
        sys_tokens = estimate_tokens(clean_sys_prompt)
        limit = 16384
        warning_threshold = int(limit * 0.8)  # 13,107 tokens

        # Keep removing oldest messages until the total size is under 16,384 tokens
        trimmed_history = []
        for msg in history_list:
            cleaned_msg = AIMessage(content=self.clean_message_content(msg.content)) if isinstance(msg, AIMessage) else HumanMessage(content=self.clean_message_content(msg.content))
            trimmed_history.append(cleaned_msg)

        while len(trimmed_history) > 0:
            hist_tokens = estimate_messages_tokens(trimmed_history)
            total = sys_tokens + hist_tokens
            if total <= limit:
                break
            trimmed_history.pop(0)

        final_hist_tokens = estimate_messages_tokens(trimmed_history)
        final_total = sys_tokens + final_hist_tokens
        
        self.last_query_estimated_context_size = final_total
        self.last_query_token_usage = final_total

        if final_total >= warning_threshold:
            print(f"\n[WARNING] [ContextManager] Active context size ({final_total} tokens) exceeds 80% of the 16,384 limit!\n")

        return trimmed_history

    def get_context_report(self) -> str:
        avg_retrieved = (self.total_memories_retrieved / self.retrieval_queries_count) if self.retrieval_queries_count > 0 else 0.0
        
        events_str = ""
        if self.summarization_events:
            for idx, ev in enumerate(self.summarization_events, 1):
                events_str += f"  {idx}. [{ev['time_str']}] Saved {ev['saved_tokens']} tokens. Summary: {ev['summary']}\n"
        else:
            events_str = "  No summarization events have occurred yet."

        report = (
            f"=== A.L.O.N.E. Context Management Report ===\n"
            f"1. Current Token Usage: {self.last_query_token_usage} tokens\n"
            f"2. Estimated Context Size Limit: 16,384 tokens (Warning at 80% / 13,107 tokens)\n"
            f"3. Summarization Events:\n{events_str}\n"
            f"4. Memory Retrieval Statistics:\n"
            f"   - Retrieval queries handled: {self.retrieval_queries_count}\n"
            f"   - Total memories retrieved: {self.total_memories_retrieved}\n"
            f"   - Average memories per query: {avg_retrieved:.2f}\n"
            f"============================================"
        )
        return report

context_manager = ContextManager()
