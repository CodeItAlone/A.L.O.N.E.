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

def _load_config(path="config.yaml"):
    if not os.path.exists(path):
        if os.path.exists("../config.yaml"):
            path = "../config.yaml"
    with open(path, "r") as f:
        return yaml.safe_load(f)

class InterruptCallbackHandler(BaseCallbackHandler):
    def __init__(self, stop_event):
        self.stop_event = stop_event

    def on_llm_start(self, *args, **kwargs):
        if self.stop_event and self.stop_event.is_set():
            raise KeyboardInterrupt("Agent task cancelled by user.")
            
    def on_tool_start(self, *args, **kwargs):
        if self.stop_event and self.stop_event.is_set():
            raise KeyboardInterrupt("Agent task cancelled by user.")

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

Recent conversation history:
{chat_history}

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

        self.prompt = PromptTemplate.from_template(template)
        
        # Initialize Agent
        self.agent = create_react_agent(self.llm, self.tools, self.prompt)
        
        callbacks = []
        if self.stop_event:
            callbacks.append(InterruptCallbackHandler(self.stop_event))
            
        self.agent_executor = AgentExecutor(
            agent=self.agent, 
            tools=self.tools, 
            verbose=True, 
            handle_parsing_errors=True,
            callbacks=callbacks,
            memory=self.memory
        )

    def run(self, user_input):
        try:
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
