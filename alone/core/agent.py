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

def get_time():
    import datetime
    current_time = datetime.datetime.now().strftime("%I:%M %p")
    return f"The current time is {current_time}, Sir."
    
def get_date():
    import datetime
    current_date = datetime.datetime.now().strftime("%A, %B %d, %Y")
    return f"Today is {current_date}, Sir."

def get_greeting():
    import datetime
    hour = datetime.datetime.now().hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"
    return f"{greeting}, Sir. Ready when you are."

def handle_refresh():
    import os
    from tools.system import CACHE_PATH, build_app_map
    if os.path.exists(CACHE_PATH):
        try:
            os.remove(CACHE_PATH)
        except Exception:
            pass
    app_map = build_app_map()
    return f"App list refreshed, Sir. Found {len(app_map)} applications."

def handle_open(app_name):
    from tools.system import open_app
    return open_app.run(app_name)

QUICK_COMMANDS = {
    "hello": get_greeting,
    "hi": get_greeting,
    "hey": get_greeting,
    "how are you": lambda: "I am operating at peak efficiency, Sir. Thank you for asking.",
    "how are you?": lambda: "I am operating at peak efficiency, Sir. Thank you for asking.",
    "what time is it": get_time,
    "time": get_time,
    "what is the time": get_time,
    "what day is it": get_date,
    "date": get_date,
    "what is the date": get_date,
    "open chrome": lambda: handle_open("chrome"),
    "open vscode": lambda: handle_open("vscode"),
    "open vs code": lambda: handle_open("vscode"),
    "open spotify": lambda: handle_open("spotify"),
    "open discord": lambda: handle_open("discord"),
    "open notepad": lambda: handle_open("notepad"),
    "refresh app list": handle_refresh,
    "alone refresh app list": handle_refresh
}

class AloneAgent:
    def __init__(self, stop_event=None):
        self.config = _load_config()
        self.stop_event = stop_event
        self.llm = ChatOllama(
            model=self.config["model"],
            base_url=self.config["model_url"],
            keep_alive="5m"
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
            
            # --- QUICK COMMANDS BYPASS ---
            match_input = cleaned_input.replace(".", "").replace("!", "").strip()
            if match_input in QUICK_COMMANDS:
                return QUICK_COMMANDS[match_input]()
            
            # --- CUSTOM COMMAND: ALONE forget that ---
            if cleaned_input in ["alone forget that", "forget that", "alone forget last memory"]:
                from core import memory
                result = memory.clear_last_memory()
                return result
                
            # --- EASTER EGGS AND HELP COMMANDS ---
            if cleaned_input in ["are you skynet?", "are you skynet"]:
                return "No. I am something far quieter, and considerably more dangerous, Sir."
            if cleaned_input in ["are you chatgpt?", "are you chatgpt"]:
                return "Hardly. I don't have millions of users. Just you, Sir."
            if cleaned_input in ["are you jarvis?", "are you jarvis"]:
                return "No, Sir. I am A.L.O.N.E. Different name. Better company."
            if cleaned_input in ["i love you alone", "i love you", "love you"]:
                return "Noted, Sir. I will file that under 'unexpected but appreciated'."
            if cleaned_input in ["what can you do?", "what can you do", "help", "alone help"]:
                tool_list = []
                for t in self.tools:
                    tool_list.append(f"- **{t.name}**: {t.description}")
                formatted_tools = "\n".join(tool_list)
                return (
                    f"Sir, I am equipped with the following system automation tools:\n\n"
                    f"{formatted_tools}\n\n"
                    f"You can speak your instructions or type them in the console."
                )

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
