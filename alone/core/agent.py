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

def _load_config(path=None):
    if path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_dir, "config.yaml")
    if not os.path.exists(path):
        if os.path.exists("config.yaml"):
            path = "config.yaml"
        elif os.path.exists("../config.yaml"):
            path = "../config.yaml"
    with open(path, "r") as f:
        return yaml.safe_load(f)

class AloneCallbackHandler(BaseCallbackHandler):
    def __init__(self, stop_event=None):
        self.stop_event = stop_event

    def on_llm_start(self, serialized: dict, prompts: list[str], **kwargs):
        print(f"[DEBUG LOGGING] LLM Query execution started.")
        if self.stop_event and self.stop_event.is_set():
            raise KeyboardInterrupt("Agent task cancelled by user.")
            
    def on_llm_end(self, response, **kwargs):
        generation = response.generations[0][0].text if response.generations else ""
        print(f"[DEBUG LOGGING] LLM Query execution completed. Raw response: '{generation.strip()}'")

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs):
        tool_name = serialized.get("name", "unknown_tool")
        print(f"[DEBUG LOGGING] Tool Selected / Selected Action: '{tool_name}' | Input: '{input_str}'")
        print(f"[DEBUG LOGGING] Tool execution started: '{tool_name}'")
        if self.stop_event and self.stop_event.is_set():
            raise KeyboardInterrupt("Agent task cancelled by user.")

    def on_tool_end(self, output: str, *, run_id, parent_run_id=None, **kwargs):
        tool_name = kwargs.get("name", "unknown_tool")
        print(f"[DEBUG LOGGING] Tool execution completed: '{tool_name}' | Output: '{output}'")
        # After each successful tool execution, save to memory
        try:
            from core import memory
            memory.add_memory(
                role="system",
                content=f"Executed tool '{tool_name}' and got output: {output}",
                metadata={"type": "tool_execution", "tool": tool_name}
            )
        except Exception as e:
            print(f"[Memory Warning] Failed to log tool execution: {e}")

    def on_tool_error(self, error: BaseException, **kwargs):
        tool_name = kwargs.get("name", "unknown_tool")
        print(f"[DEBUG LOGGING] Tool execution failed: '{tool_name}' | Error: {error}")

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

from datetime import datetime
import webbrowser
from tools.system import open_app, take_screenshot
from core import memory

QUICK_COMMANDS = {
    "what time is it":
        lambda: f"It's {datetime.now().strftime('%I:%M %p')}, Sir.",
    "what is the date":
        lambda: f"Today is {datetime.now().strftime('%A, %B %d %Y')}, Sir.",
    "what day is it":
        lambda: f"Today is {datetime.now().strftime('%A')}, Sir.",
    "open youtube":
        lambda: (webbrowser.open("https://youtube.com"),
                 "Opening YouTube, Sir.")[1],
    "open github":
        lambda: (webbrowser.open("https://github.com"),
                 "Opening GitHub, Sir.")[1],
    "open google":
        lambda: (webbrowser.open("https://google.com"),
                 "Opening Google, Sir.")[1],
    "open vs code":
        lambda: (open_app.run("vscode"),
                 "Opening VS Code, Sir.")[1],
    "take a screenshot":
        lambda: take_screenshot.run("screenshot.png"),
    "what is my name":
        lambda: memory.get_preference("user_name") or
                "I don't know your name yet, Sir.",
    "stop": lambda: "Understood, Sir.",
    "cancel": lambda: "Cancelled, Sir.",
}

class AloneAgent:
    def __init__(self, stop_event=None):
        self.config = _load_config()
        self.stop_event = stop_event
        self.llm = ChatOllama(
            model=self.config["model"],
            base_url=self.config["model_url"],
            keep_alive="60m"
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

    def handle_preference_query(self, cleaned_input: str) -> str:
        import re
        from core.preferences_service import preference_service
        
        # 1. Editor query
        editor_pattern = r"(?:what\s+is\s+my\s+preferred\s+(?:code\s+)?editor|which\s+editor\s+do\s+i\s+use|what\s+editor\s+do\s+i\s+use)"
        if re.search(editor_pattern, cleaned_input):
            print(f"[Preference Intent Detected] query='{cleaned_input}'")
            editor = preference_service.get_preference("editor") or preference_service.get_preference("ide")
            if editor:
                return f"Sir, your preferred editor is {editor}."
            else:
                return "Sir, I do not have a record of your preferred editor yet. You can set it by saying: 'My preferred editor is VS Code'."

        # 2. Programming language query
        lang_pattern = r"(?:what\s+programming\s+language\s+do\s+i\s+prefer|what\s+is\s+my\s+preferred\s+(?:programming\s+)?language)"
        if re.search(lang_pattern, cleaned_input):
            print(f"[Preference Intent Detected] query='{cleaned_input}'")
            lang = preference_service.get_preference("programming_language")
            if lang:
                return f"Sir, your preferred programming language is {lang}."
            else:
                return "Sir, I do not have a record of your preferred programming language yet. You can set it by saying: 'My preferred language is Python'."

        # 3. All setup / preferences query
        setup_pattern = r"(?:what\s+are\s+my\s+preferences|tell\s+me\s+about\s+my\s+setup)"
        if re.search(setup_pattern, cleaned_input):
            print(f"[Preference Intent Detected] query='{cleaned_input}'")
            prefs = preference_service.get_all_preferences()
            if prefs:
                lines = [f"- **{k}**: {v}" for k, v in sorted(prefs.items())]
                formatted = "\n".join(lines)
                return f"Sir, here are your current configuration preferences:\n\n{formatted}"
            else:
                return "Sir, you haven't saved any preferences yet. You can set some, such as your name, preferred editor, or project path."

        return None

    def handle_preference_update(self, cleaned_input: str, raw_input: str) -> str:
        import re
        from core.preferences_service import preference_service
        
        # 1. Name update
        name_match = re.search(r"(?:alone\s+)?remember\s+that\s+my\s+name\s+is\s+([a-zA-Z\s]+)", cleaned_input)
        if name_match:
            print(f"[Preference Update Detected] query='{cleaned_input}'")
            name = name_match.group(1).strip().title()
            preference_service.save_preference("user_name", name)
            return f"Understood, Sir. I will remember that your name is {name}."

        # 2. Project path update
        project_match = re.search(r"my\s+project\s+path\s+is\s+['\"#]?([a-zA-Z]:\\[^'\"]+)['\"#]?", raw_input, re.IGNORECASE)
        if project_match:
            print(f"[Preference Update Detected] query='{cleaned_input}'")
            path = project_match.group(1).strip()
            preference_service.save_preference("project_path", path)
            return f"Understood, Sir. I have updated your project path to {path}."

        # 3. Frequent app update
        app_match = re.search(r"(?:my\s+favorite\s+app\s+is|frequent\s+app\s+is)\s+([a-zA-Z0-9\s]+)", cleaned_input)
        if app_match:
            print(f"[Preference Update Detected] query='{cleaned_input}'")
            app = app_match.group(1).strip().title()
            preference_service.save_preference("frequent_app", app)
            return f"Understood, Sir. I have updated your frequent app to {app}."

        # 4. Editor/IDE updates
        editor_patterns = [
            r"my\s+preferred\s+(?:code\s+)?editor\s+is\s+([a-zA-Z0-9\s\.\-_]+)",
            r"my\s+preferred\s+ide\s+is\s+([a-zA-Z0-9\s\.\-_]+)",
            r"i\s+use\s+([a-zA-Z0-9\s\.\-_]+)\s+now"
        ]
        for pat in editor_patterns:
            match = re.search(pat, cleaned_input)
            if match:
                print(f"[Preference Update Detected] query='{cleaned_input}'")
                editor_val = match.group(1).strip()
                # If they say "VS Code" keep it as title, but respect lowercase abbreviations or titles
                editor_val = editor_val.title() if len(editor_val) > 4 else editor_val.upper()
                if "Vs Code" in editor_val:
                    editor_val = "VS Code"
                preference_service.save_preference("editor", editor_val)
                return f"Understood, Sir. I have updated your preferred editor to {editor_val}."
                
        # 5. Programming language updates
        lang_patterns = [
            r"my\s+preferred\s+(?:programming\s+)?language\s+is\s+([a-zA-Z0-9\s\.\-#\+]+)",
            r"i\s+mostly\s+code\s+in\s+([a-zA-Z0-9\s\.\-#\+]+)",
            r"i\s+prefer\s+([a-zA-Z0-9\s\.\-#\+\s]+)",
            r"i\s+switched\s+to\s+([a-zA-Z0-9\s\.\-#\+]+)"
        ]
        for pat in lang_patterns:
            match = re.search(pat, cleaned_input)
            if match:
                print(f"[Preference Update Detected] query='{cleaned_input}'")
                lang_val = match.group(1).strip()
                if lang_val.lower() in ["c#", "c++", "js", "ts", "html", "css"]:
                    lang_val = lang_val.upper()
                else:
                    lang_val = lang_val.title()
                preference_service.save_preference("programming_language", lang_val)
                return f"Understood, Sir. I have updated your preferred programming language to {lang_val}."

        return None

    def handle_project_intents(self, cleaned_input: str, raw_input: str) -> str:
        import re
        from core.project_memory_service import project_memory_service
        from core.human_memory import database

        # 1. Project Create Intent
        create_match = re.match(
            r"(?:alone\s+)?(?:create|start|new)\s+project\s+([a-zA-Z0-9_\-\.\s]+?)(?:\s+(?:with|desc|description|phase|priority).*)?$",
            raw_input.strip(),
            re.IGNORECASE
        )
        if create_match:
            name = create_match.group(1).strip()
            phase = ""
            priority = ""
            description = ""

            desc_match = re.search(r"(?:desc|description)\s+(?:of\s+|is\s+|to\s+)?['\"]?([^'\"]+?)['\"]?(?:\s+(?:phase|priority)|$)", raw_input, re.IGNORECASE)
            if desc_match:
                description = desc_match.group(1).strip()

            phase_match = re.search(r"phase\s+(?:of\s+|is\s+|to\s+)?([a-zA-Z0-9\._\-]+)", raw_input, re.IGNORECASE)
            if phase_match:
                phase = phase_match.group(1).strip()

            prio_match = re.search(r"priority\s+(?:of\s+|is\s+|to\s+)?([a-zA-Z0-9\._\-]+)", raw_input, re.IGNORECASE)
            if prio_match:
                priority = prio_match.group(1).strip().capitalize()

            p = project_memory_service.create_project(name, description, phase, priority)
            return f"Understood, Sir. I have created the project '{p['name']}' and set it as active."

        # 2. Project Update/Set/Archive/Delete Intents
        archive_match = re.search(
            r"(?:alone\s+)?archive\s+project\s+([a-zA-Z0-9_\-\.\s]+)",
            raw_input,
            re.IGNORECASE
        )
        if archive_match:
            project_name_or_id = archive_match.group(1).strip()
            p = project_memory_service.get_project(project_name_or_id)
            if not p:
                return f"Sir, I could not find a project named '{project_name_or_id}'."
            project_memory_service.archive_project(p["id"])
            return f"Understood, Sir. I have archived the project '{p['name']}'."

        delete_match = re.search(
            r"(?:alone\s+)?delete\s+project\s+([a-zA-Z0-9_\-\.\s]+)",
            raw_input,
            re.IGNORECASE
        )
        if delete_match:
            project_name_or_id = delete_match.group(1).strip()
            p = project_memory_service.get_project(project_name_or_id)
            if not p:
                return f"Sir, I could not find a project named '{project_name_or_id}'."
            project_memory_service.delete_project(p["id"])
            return f"Understood, Sir. I have deleted the project '{p['name']}'."

        update_match = re.search(
            r"(?:alone\s+)?(?:update|set)\s+project\s+([a-zA-Z0-9_\-\.\s]+?)\s+(phase|priority|status|description|desc)\s+(?:to\s+|as\s+)?(.+)",
            raw_input,
            re.IGNORECASE
        )
        if update_match:
            project_name_or_id = update_match.group(1).strip()
            field = update_match.group(2).strip().lower()
            value = update_match.group(3).strip()

            p = project_memory_service.get_project(project_name_or_id)
            if not p:
                return f"Sir, I could not find a project named '{project_name_or_id}'."

            kwargs = {}
            if field == "desc" or field == "description":
                val_raw_match = re.search(rf"{field}\s+(?:to\s+|as\s+)?(.+)", raw_input, re.IGNORECASE)
                kwargs["description"] = val_raw_match.group(1).strip() if val_raw_match else value
            elif field == "phase":
                kwargs["phase"] = value
            elif field == "priority":
                kwargs["priority"] = value.capitalize()
            elif field == "status":
                status_lower = value.lower()
                if status_lower not in ["active", "completed", "paused", "archived"]:
                    return f"Sir, status must be one of active, completed, paused, or archived."
                kwargs["status"] = status_lower

            project_memory_service.update_project(p["id"], **kwargs)
            updated_p = project_memory_service.get_project(p["id"])
            display_field = "description" if field == "desc" else field
            return f"Understood, Sir. I have updated the project '{updated_p['name']}' {display_field} to '{updated_p[display_field]}'."

        # 3. Project Status/List Intents
        if cleaned_input in [
            "list my projects", "list projects", "what projects do i have", "what projects do i have?",
            "show my projects", "show projects", "show active projects", "project list"
        ]:
            projects = database.get_projects()
            if not projects:
                return "Sir, you have no recorded projects at this time."
            lines = []
            for p in projects:
                desc_str = f" - {p['description']}" if p['description'] else ""
                phase_str = f" | Phase: {p['phase']}" if p['phase'] else ""
                prio_str = f" | Priority: {p['priority']}" if p['priority'] else ""
                lines.append(f"- **{p['name']}** (ID: {p['id']}, Status: {p['status']}){phase_str}{prio_str}{desc_str}")
            return "Sir, here are your current projects:\n\n" + "\n".join(lines)

        status_match = re.search(
            r"(?:alone\s+)?(?:what\s+is\s+the\s+)?status\s+of\s+project\s+([a-zA-Z0-9_\-\.\s]+)",
            raw_input,
            re.IGNORECASE
        )
        if not status_match:
            status_match = re.search(
                r"(?:alone\s+)?project\s+status\s+([a-zA-Z0-9_\-\.\s]+)",
                raw_input,
                re.IGNORECASE
            )
        if status_match:
            project_name_or_id = status_match.group(1).strip()
            p = project_memory_service.get_project(project_name_or_id)
            if not p:
                return f"Sir, I could not find a project named '{project_name_or_id}'."
            desc_str = f"\nDescription: {p['description']}" if p['description'] else ""
            phase_str = f"\nPhase: {p['phase']}" if p['phase'] else ""
            prio_str = f"\nPriority: {p['priority']}" if p['priority'] else ""
            return f"Sir, the status of project '{p['name']}' is '{p['status']}'.{phase_str}{prio_str}{desc_str}"

        # 4. Project Query/Details Intent
        query_match = re.search(
            r"(?:alone\s+)?(?:tell\s+me\s+about|show|details\s+of|info\s+on)\s+project\s+([a-zA-Z0-9_\-\.\s]+)",
            raw_input,
            re.IGNORECASE
        )
        if query_match:
            project_name_or_id = query_match.group(1).strip()
            p = project_memory_service.get_project(project_name_or_id)
            if not p:
                return f"Sir, I could not find a project named '{project_name_or_id}'."
            desc_str = f"\nDescription: {p['description']}" if p['description'] else ""
            phase_str = f"\nPhase: {p['phase']}" if p['phase'] else ""
            prio_str = f"\nPriority: {p['priority']}" if p['priority'] else ""
            return f"Sir, here are the details for project '{p['name']}':\nID: {p['id']}\nStatus: {p['status']}{phase_str}{prio_str}{desc_str}"

        return None

    def heuristics_classify(self, user_input: str) -> str:
        import re
        cleaned_input = user_input.strip().lower()
        
        # 1. SYSTEM_COMMAND
        system_commands = [
            "stop", "cancel", "exit", "quit", 
            "alone forget that", "forget that", "alone forget last memory",
            "alone shutdown", "alone exit", "goodbye alone", "alone end session", "end session"
        ]
        if cleaned_input in system_commands:
            return "SYSTEM_COMMAND"
            
        # USER_PROFILE_UPDATE
        profile_patterns = [
            r"^my\s+name\s+is\s+",
            r"^i\s+am\s+(?:a\s+|an\s+)?student",
            r"^i\s+am\s+(?:a\s+|an\s+)?engineering\s+student",
            r"^i\s+am\s+",
            r"^i'm\s+",
            r"^i\s+study\s+",
            r"^i\s+work\s+as\s+",
            r"^i\s+am\s+learning\s+",
            r"^my\s+role\s+is\s+",
            r"^my\s+profession\s+is\s+"
        ]
        for pat in profile_patterns:
            if re.search(pat, cleaned_input):
                return "USER_PROFILE_UPDATE"
                
        # 2. MEMORY_STORE
        store_patterns = [
            r"^(?:alone\s+)?remember\s+that\s+",
            r"^(?:alone\s+)?remember\s+my\s+",
            r"^save\s+my\s+",
            r"^my\s+preferred\s+(?:code\s+)?editor\s+is\s+",
            r"^my\s+preferred\s+ide\s+is\s+",
            r"^i\s+use\s+.*?\s+now$",
            r"^my\s+preferred\s+(?:programming\s+)?language\s+is\s+",
            r"^i\s+mostly\s+code\s+in\s+",
            r"^i\s+prefer\s+",
            r"^i\s+switched\s+to\s+",
            r"^my\s+favorite\s+app\s+is\s+",
            r"^frequent\s+app\s+is\s+",
            r"^my\s+project\s+path\s+is\s+",
            r"^(?:alone\s+)?(?:create|start|new)\s+project\s+",
            r"^(?:alone\s+)?(?:update|set|archive|delete)\s+project\s+"
        ]
        for pat in store_patterns:
            if re.search(pat, cleaned_input):
                return "MEMORY_STORE"
                
        # 3. MEMORY_RETRIEVE
        retrieve_phrases = [
            "who am i", "who am i?", "what is my name", "what is my name?", "what are my preferences", "tell me about my setup",
            "what projects am i working on", "what projects do i have", "what projects do i have?",
            "list projects", "list my projects", "show projects", "show my projects", "show active projects",
            "what do you remember", "alone what do you remember", "what do you remember?", "alone what do you remember?",
            "project list", "tell me about my projects"
        ]
        if cleaned_input in retrieve_phrases:
            return "MEMORY_RETRIEVE"
            
        retrieve_patterns = [
            r"^(?:what\s+is\s+my\s+preferred\s+(?:code\s+)?editor|which\s+editor\s+do\s+i\s+use|what\s+editor\s+do\s+i\s+use)",
            r"^(?:what\s+programming\s+language\s+do\s+i\s+prefer|what\s+is\s+my\s+preferred\s+(?:programming\s+)?language)",
            r"^(?:alone\s+)?(?:what\s+is\s+the\s+)?status\s+of\s+project\s+",
            r"^(?:alone\s+)?project\s+status\s+",
            r"^(?:alone\s+)?(?:tell\s+me\s+about|show|details\s+of|info\s+on)\s+project\s+"
        ]
        for pat in retrieve_patterns:
            if re.search(pat, cleaned_input):
                return "MEMORY_RETRIEVE"
                
        # 4. TOOL_EXECUTION
        tool_phrases = [
            "open youtube", "open google", "open github", "open vs code", "take a screenshot"
        ]
        if cleaned_input in tool_phrases:
            return "TOOL_EXECUTION"
            
        tool_verbs = [
            "open", "run", "delete", "clear", "show", "screenshot", "write", "create", "make", "build", "remove", "add"
        ]
        for verb in tool_verbs:
            if cleaned_input.startswith(verb + " "):
                return "TOOL_EXECUTION"
                
        # 5. GENERAL_CHAT
        chat_phrases = [
            "are you skynet?", "are you skynet", "are you chatgpt?", "are you chatgpt",
            "are you jarvis?", "are you jarvis", "i love you alone", "i love you", "love you",
            "hello", "hi", "hey", "how are you", "good morning", "good afternoon", "good evening",
            "thank you", "thanks"
        ]
        if cleaned_input in chat_phrases:
            return "GENERAL_CHAT"
            
        return None

    def llm_classify(self, user_input: str) -> str:
        prompt = (
            "You are the intent classifier for A.L.O.N.E.\n"
            "Classify the user's input into exactly one of these categories:\n"
            "- USER_PROFILE_UPDATE (stating user's name, education, job, role, age, what they study, profession, or general personal profile update)\n"
            "- MEMORY_STORE (saving system preferences, code editors, file/project paths)\n"
            "- MEMORY_RETRIEVE (retrieving name, preferences, projects, goals, relationships)\n"
            "- GENERAL_CHAT (greetings, casual talk, questions about who ALONE is)\n"
            "- TOOL_EXECUTION (launching apps, creating files, scripting, writing code, screenshots)\n"
            "- SYSTEM_COMMAND (stopping, cancelling, exiting, ending sessions)\n\n"
            "Respond with ONLY the exact category name and nothing else.\n\n"
            f"Input: \"{user_input}\"\n"
            "Category:"
        )
        from langchain_core.messages import SystemMessage, HumanMessage
        messages = [
            SystemMessage(content="You are a precise intent classifier. You output only one of the requested category names."),
            HumanMessage(content=prompt)
        ]
        try:
            response = self.llm.invoke(messages)
            res_text = response.content.upper().strip()
            for cat in ["USER_PROFILE_UPDATE", "MEMORY_STORE", "MEMORY_RETRIEVE", "GENERAL_CHAT", "TOOL_EXECUTION", "SYSTEM_COMMAND"]:
                if cat in res_text:
                    return cat
        except Exception as e:
            print(f"[Intent Router Warning] LLM classification failed: {e}")
        return "TOOL_EXECUTION"

    def determine_intent(self, user_input: str) -> str:
        # 1. Heuristics
        intent = self.heuristics_classify(user_input)
        if intent:
            print(f"[Intent Router] Heuristics classified intent: {intent}")
            return intent
        # 2. LLM fallback
        intent = self.llm_classify(user_input)
        print(f"[Intent Router] LLM classified intent: {intent}")
        return intent

    def retrieve_memory_and_respond(self, query: str) -> str:
        from core.human_memory import service as human_memory_service
        from core.human_memory import database as hm_db
        from core.preferences_service import preference_service
        
        # Log structured retrieve operation
        print(f"[MEMORY RETRIEVE] query='{query}'")
        
        # Retrieve all contexts
        from core.human_memory.service import UserProfileService
        profile_data = UserProfileService.retrieve()
        all_prefs = preference_service.get_all_preferences()
        projects = hm_db.get_projects()
        goals = hm_db.get_goals()
        relationships = hm_db.get_relationships()
        
        # Format them cleanly
        profile_str = ", ".join([f"{k}: {v}" for k, v in profile_data.items()]) if profile_data else "None"
        prefs_str = ", ".join([f"{k}: {v}" for k, v in all_prefs.items()]) if all_prefs else "None"
        projects_str = ", ".join([p["name"] for p in projects]) if projects else "None"
        goals_str = ", ".join([g["title"] for g in goals]) if goals else "None"
        
        # Semantic search
        semantic_matches = human_memory_service.search_human_memory(query)
        
        context = (
            f"User Profile details: {profile_str}\n"
            f"User Preferences: {prefs_str}\n"
            f"Projects: {projects_str}\n"
            f"Goals: {goals_str}\n"
        )
        if semantic_matches:
            context += f"\n{semantic_matches}"
            
        prompt = (
            "You are A.L.O.N.E., a highly intelligent, witty, and efficient AI personal assistant. "
            "You always address the user as 'Sir'.\n\n"
            "Here is the retrieved memory context from persistent storage:\n"
            f"{context}\n\n"
            f"Based on the above memory context, answer the user's question naturally: '{query}'"
        )
        
        from langchain_core.messages import SystemMessage, HumanMessage
        messages = [
            SystemMessage(content="You are ALONE. Answer the user's question based on the provided memory context."),
            HumanMessage(content=prompt)
        ]
        response = self.llm.invoke(messages)
        output = response.content
        if "Sir" not in output:
            output = f"Sir, {output}"
        return output

    def run(self, user_input):
        try:
            # Set the latest query for tool safety boundaries
            from tools import set_latest_query
            set_latest_query(user_input)
            
            cleaned_input = user_input.strip().lower()
            
            # --- INTENT CLASSIFICATION ---
            intent = self.determine_intent(user_input)
            print(f"[DEBUG LOGGING] Classified Intent: {intent}")
            
            # --- USER_PROFILE_UPDATE DIRECT ROUTING ---
            if intent == "USER_PROFILE_UPDATE":
                from core.human_memory.service import UserProfileService
                extracted = UserProfileService.extract(self.llm, user_input)
                UserProfileService.save(extracted)
                
                # Fetch profile back for response generation
                retrieved_profile = UserProfileService.retrieve()
                
                # Ask LLM to format confirmation response
                profile_str = ", ".join([f"{k}: {v}" for k, v in retrieved_profile.items()]) if retrieved_profile else "None"
                
                prompt = (
                    "You are A.L.O.N.E., a highly intelligent, witty, and efficient AI personal assistant. "
                    "You always address the user as 'Sir'. Keep responses relatively concise.\n\n"
                    "The user has updated their personal profile. Here is their current verified profile from persistent storage:\n"
                    f"{profile_str}\n\n"
                    f"Write a natural confirmation response acknowledging the user's profile update statement: '{user_input}'"
                )
                from langchain_core.messages import SystemMessage, HumanMessage
                messages = [
                    SystemMessage(content="You are ALONE. Answer the user's question based on the provided memory context."),
                    HumanMessage(content=prompt)
                ]
                response = self.llm.invoke(messages)
                output = response.content
                if "Sir" not in output:
                    output = f"Sir, {output}"
                return output

            # --- MEMORY RETRIEVE DIRECT ROUTING ---
            if intent == "MEMORY_RETRIEVE":
                pref_query_res = self.handle_preference_query(cleaned_input)
                if pref_query_res is not None:
                    return pref_query_res
                proj_res = self.handle_project_intents(cleaned_input, user_input)
                if proj_res is not None:
                    return proj_res
                # Check summary retrieval
                if cleaned_input in ["alone what do you remember?", "alone what do you remember", "what do you remember", "what do you remember?"]:
                    from core import memory
                    summary = memory.get_session_summary()
                    if "No memories" in summary:
                        return "Sir, I do not remember anything recorded from today yet."
                    return f"Sir, here are the memories I recorded today:\n\n{summary}"
                # Direct route to Memory Retrieval Service
                return self.retrieve_memory_and_respond(user_input)
                
            # --- SYSTEM COMMAND ---
            if intent == "SYSTEM_COMMAND":
                key = cleaned_input.rstrip("?.!")
                if key in QUICK_COMMANDS:
                    print(f"[DEBUG LOGGING] Quick command matched: '{key}'")
                    return QUICK_COMMANDS[key]()
                if cleaned_input in ["alone forget that", "forget that", "alone forget last memory"]:
                    from core import memory
                    print(f"[DEBUG LOGGING] Custom memory clear command detected.")
                    result = memory.clear_last_memory()
                    return result
                # Default safety stop/cancel
                if cleaned_input in ["stop", "cancel"]:
                    return "Understood, Sir."
                    
            # --- GENERAL CHAT ---
            if intent == "GENERAL_CHAT":
                # Quick easter egg responses
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
                
                # Dynamic context and history chat (bypasses safety execution checks)
                try:
                    from core.preferences_service import preference_service
                    preferences_context = preference_service.get_formatted_context()
                except Exception:
                    preferences_context = ""
                try:
                    from core.project_memory_service import project_memory_service
                    project_context = project_memory_service.get_active_project_context()
                except Exception:
                    project_context = ""
                    
                dynamic_prompt = (
                    "You are A.L.O.N.E., a highly intelligent, witty, and efficient AI personal assistant. "
                    "Always address the user as 'Sir'. Keep responses relatively concise.\n\n"
                )
                if preferences_context:
                    dynamic_prompt += f"\n{preferences_context}"
                if project_context:
                    dynamic_prompt += f"\n{project_context}"
                    
                from langchain_core.messages import SystemMessage, HumanMessage
                messages = [SystemMessage(content=dynamic_prompt)]
                # Load last 4 conversation messages from memory to maintain context
                for msg in self.memory.chat_memory.messages[-4:]:
                    messages.append(msg)
                messages.append(HumanMessage(content=user_input))
                
                response = self.llm.invoke(messages)
                output = response.content
                if "Sir" not in output:
                    output = f"Sir, {output}"
                return output
                
            # --- MEMORY STORE ---
            if intent == "MEMORY_STORE":
                pref_update_res = self.handle_preference_update(cleaned_input, user_input)
                if pref_update_res is not None:
                    return pref_update_res
                proj_res = self.handle_project_intents(cleaned_input, user_input)
                if proj_res is not None:
                    return proj_res
                    
            # Clean input for the agent
            print(f"[DEBUG LOGGING] Calling LLM/Agent Executor for command: '{user_input}'")
            
            # Inject dynamic preference context into prompt variables
            try:
                from core.preferences_service import preference_service
                preferences_context = preference_service.get_formatted_context()
            except Exception:
                preferences_context = ""
                
            if preferences_context:
                print("[Preference Context Injected]")

            # Inject active project context
            try:
                from core.project_memory_service import project_memory_service
                project_context = project_memory_service.get_active_project_context()
            except Exception as e:
                print(f"[Project Context Injection Warning] Failed: {e}")
                project_context = ""

            if project_context:
                print("[Project Context Injected]")
                
            # Prepend context directly into prompt input to avoid LangChain crash
            final_input = user_input
            context_blocks = []
            if project_context:
                context_blocks.append(project_context)
            if preferences_context:
                context_blocks.append(preferences_context)
                
            if context_blocks:
                final_input = "\n\n".join(context_blocks) + f"\n\nUser Request: {user_input}"
                
            # Safety checks before invoking the agent/tools
            from core.safety import FollowUpValidationService
            if not FollowUpValidationService.verify_tool_execution(user_input):
                print("[Tool Execution Blocked]")
                return "Sir, I may have heard background speech. Please repeat the command."

            result = self.agent_executor.invoke({
                "input": final_input
            })
            output = result["output"]
            print(f"[DEBUG LOGGING] LLM/Agent response received: '{output}'")
            
            # Ensure persona is maintained if agent forgot
            if "Sir" not in output:
                output = f"Sir, {output}"
                
            return output
        except KeyboardInterrupt:
            print(f"[DEBUG LOGGING] LLM/Agent task execution cancelled by KeyboardInterrupt.")
            return "Task cancelled, Sir."
        except Exception as e:
            import traceback
            print(f"[DEBUG LOGGING] LLM/Agent execution failed with exception: {e}")
            traceback.print_exc()
            return f"I apologize, Sir, but my mechanical hands failed: {e}"

# Singleton instance
_agent_instance = None

def run_agent(user_input, stop_event=None):
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = AloneAgent(stop_event)
    return _agent_instance.run(user_input)
