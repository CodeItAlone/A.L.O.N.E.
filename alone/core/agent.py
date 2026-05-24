import yaml
import os
import sys

# Ensure project root is in path for tool imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from langchain.agents import AgentExecutor, create_react_agent
except (ImportError, ModuleNotFoundError):
    from langchain_classic.agents import AgentExecutor, create_react_agent  # type: ignore

from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.callbacks import BaseCallbackHandler
try:
    from langchain.memory import ConversationBufferMemory  # type: ignore
except (ImportError, ModuleNotFoundError):
    from langchain_classic.memory import ConversationBufferMemory  # type: ignore
from tools import ALL_TOOLS

try:
    from langchain.agents.output_parsers import ReActSingleInputOutputParser  # type: ignore
except (ImportError, ModuleNotFoundError):
    try:
        from langchain_classic.agents.output_parsers import ReActSingleInputOutputParser  # type: ignore
    except (ImportError, ModuleNotFoundError):
        from langchain.agents.react.agent import ReActSingleInputOutputParser  # type: ignore

from langchain_core.agents import AgentFinish, AgentAction

class ForgivingReActOutputParser(ReActSingleInputOutputParser):
    def parse(self, text: str):
        try:
            return super().parse(text)
        except Exception as e:
            text_lower = text.lower()
            # If standard ReAct parser fails and no 'action:' exists, the model was responding directly.
            # Intercept it and treat it as the final answer immediately, preventing hallucinatory tool loops.
            if "action:" not in text_lower:
                clean_text = text
                if "thought:" in text_lower:
                    idx = text_lower.find("thought:")
                    remaining = text[idx + 8:].strip()
                    if remaining.startswith("Do I need to use a tool?"):
                        lines = remaining.split("\n")
                        non_empty_lines = [l.strip() for l in lines if l.strip()]
                        if len(non_empty_lines) > 1:
                            clean_text = "\n".join(non_empty_lines[1:])
                        else:
                            clean_text = remaining
                    else:
                        clean_text = remaining
                
                # Strip common leftover prompt prefix tags
                for garbage in ["Final Answer:", "final answer:", "Final answer:", "Thought:", "thought:"]:
                    clean_text = clean_text.replace(garbage, "")
                clean_text = clean_text.strip()
                
                return AgentFinish(
                    return_values={"output": clean_text},
                    log=text
                )
            # Re-raise standard formatting exceptions if there IS an 'action:' keyword but it failed parsing
            raise e

def _load_config(path="config.yaml"):
    if not os.path.exists(path):
        if os.path.exists("../config.yaml"):
            path = "../config.yaml"
    with open(path, "r") as f:
        return yaml.safe_load(f)

class AloneCallbackHandler(BaseCallbackHandler):
    def __init__(self, stop_event=None):
        self.stop_event = stop_event

    def on_llm_start(self, *args, **kwargs):
        if self.stop_event and self.stop_event.is_set():
            raise KeyboardInterrupt("Agent task cancelled by user.")
            
    def on_tool_start(self, *args, **kwargs):
        if self.stop_event and self.stop_event.is_set():
            raise KeyboardInterrupt("Agent task cancelled by user.")

    def on_tool_end(self, output: str, *, run_id, parent_run_id=None, **kwargs):
        # After each successful tool execution, save to memory
        try:
            from core import memory
            tool_name = kwargs.get("name", "unknown_tool")
            memory.add_memory(
                role="system",
                content=f"Executed tool '{tool_name}' and got output: {output}",
                metadata={"type": "tool_execution", "tool": tool_name}
            )
        except Exception as e:
            print(f"[Memory Warning] Failed to log tool execution: {e}")

class AloneAgent:
    def __init__(self, stop_event=None):
        self.config = _load_config()
        self.stop_event = stop_event
        self.llm = ChatOllama(
            model=self.config["model"],
            base_url=self.config["model_url"]
        )
        self.tools = ALL_TOOLS
        
        # Initialize Memory
        self.memory = ConversationBufferMemory(memory_key="chat_history")
        
        template = """You are A.L.O.N.E., a highly intelligent, witty, and efficient AI personal assistant. 
You always address the user as 'Sir'. 
Your goal is to assist the user by using your tools effectively.

You have access to the following tools:

{tools}

To use a tool, please use the following format:

Thought: Do I need to use a tool? Yes
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: Do I need to use a tool? No
Final Answer: [Your final response to the user, addressing them as 'Sir']

When using tools, ensure the 'Action Input' is ONLY the value required by the tool, with no extra text or comments. 
For tools requiring multiple inputs (like write_file or write_code), use a comma to separate them: 'value1, value2'.

CRITICAL SECURITY RULE: Under no circumstances should you run any tools or execute shell commands unless the user explicitly requested that specific action in their latest question. Never perform additional, unsolicited actions or explore the repository unless specifically instructed by the user.

Recent conversation history:
{chat_history}

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

        self.prompt = PromptTemplate.from_template(template)
        
        # Initialize Agent with our Forgiving Output Parser
        self.agent = create_react_agent(self.llm, self.tools, self.prompt, output_parser=ForgivingReActOutputParser())
        
        callbacks = [AloneCallbackHandler(self.stop_event)]
            
        self.agent_executor = AgentExecutor(
            agent=self.agent, 
            tools=self.tools, 
            verbose=True, 
            handle_parsing_errors=True,
            max_iterations=4,  # Strictly limit iterations to prevent infinite hallucination loops
            callbacks=callbacks,
            memory=self.memory
        )

    def run(self, user_input):
        try:
            # Set the latest query for tool safety boundaries
            from tools import set_latest_query
            set_latest_query(user_input)
            
            cleaned_input = user_input.strip().lower()
            
            # --- CUSTOM COMMAND: ALONE forget that ---
            if cleaned_input in ["alone forget that", "forget that", "alone forget last memory"]:
                from core import memory
                result = memory.clear_last_memory()
                return result
                
            # --- CUSTOM COMMAND: ALONE what do you remember? ---
            if cleaned_input in ["alone what do you remember?", "alone what do you remember", "what do you remember", "what do you remember?"]:
                from core import memory
                summary = memory.get_session_summary()
                if "No memories" in summary:
                    return "Sir, I do not remember anything recorded from today yet."
                return f"Sir, here are the memories I recorded today:\n\n{summary}"
                
            # --- CUSTOM COMMAND: ALONE remember that my name is [name] ---
            import re
            name_match = re.search(r"(?:alone\s+)?remember\s+that\s+my\s+name\s+is\s+([a-zA-Z\s]+)", user_input.lower())
            if name_match:
                name = name_match.group(1).strip().title()
                from core import memory
                memory.save_preference("user_name", name)
                return f"Understood, Sir. I will remember that your name is {name}."
                
            # Pattern-match other preference categories (paths, frequent apps) mentioned in voice/text
            project_match = re.search(r"my\s+project\s+path\s+is\s+['\"#]?([a-zA-Z]:\\[^'\"]+)['\"#]?", user_input, re.IGNORECASE)
            if project_match:
                path = project_match.group(1).strip()
                from core import memory
                memory.save_preference("project_path", path)
                
            app_match = re.search(r"(?:my\s+favorite\s+app\s+is|frequent\s+app\s+is)\s+([a-zA-Z0-9\s]+)", user_input, re.IGNORECASE)
            if app_match:
                app = app_match.group(1).strip()
                from core import memory
                memory.save_preference("frequent_app", app)
            
            # Clean input for the agent
            result = self.agent_executor.invoke({"input": user_input})
            output = result["output"]
            
            # Ensure persona is maintained if agent forgot
            if "Sir" not in output:
                output = f"Sir, {output}"
                
            return output
        except KeyboardInterrupt:
            return "Task cancelled, Sir."
        except Exception as e:
            return f"I apologize, Sir, but my mechanical hands failed: {e}"

# Singleton instance
_agent_instance = None

def run_agent(user_input, stop_event=None):
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = AloneAgent(stop_event)
    return _agent_instance.run(user_input)
