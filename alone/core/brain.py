import yaml
import json
import os
import ollama
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

class Brain:
    def __init__(self, config_path=None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if config_path is None:
            config_path = os.path.join(base_dir, "config.yaml")
        self.config = self._load_config(config_path)
        self.history_file = os.path.join(base_dir, self.config.get("history_file", "history.json"))
        self.max_history = self.config.get("max_history", 20)
        
        # Initialize Ollama client
        self.client = ChatOllama(
            model=self.config["model"],
            base_url=self.config["model_url"],
            keep_alive="60m"
        )
        
        # ALONE System Prompt
        self.system_prompt = self.config.get("system_prompt", (
            "You are A.L.O.N.E., a highly intelligent, witty, and "
            "efficient AI personal assistant running locally on the "
            "user's laptop. You are concise, sharp, and always address "
            "the user as 'Sir'. You have a dry, calm, and composed "
            "personality. Never say you are an AI language model. "
            "You are ALONE."
        ))
        
        # Load or initialize history
        self.history = self._load_history()
        
        # Perform Health Check and ensure model exists
        self._health_check()

    def _load_config(self, path):
        if not os.path.exists(path):
            if os.path.exists("config.yaml"):
                path = "config.yaml"
            elif os.path.exists("../config.yaml"):
                path = "../config.yaml"
            else:
                raise FileNotFoundError(f"Config file not found at {path}")
        with open(path, "r") as f:
            return yaml.safe_load(f)

    def _load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r") as f:
                    data = json.load(f)
                    history = []
                    for msg in data:
                        if msg["role"] == "user":
                            history.append(HumanMessage(content=msg["content"]))
                        elif msg["role"] == "assistant":
                            history.append(AIMessage(content=msg["content"]))
                    return history
            except Exception as e:
                print(f"[Warning] Failed to load history: {e}. Starting fresh.")
        return []

    def _save_history(self):
        data = []
        # We only save Human and AI messages, System prompt is added on each chat
        for msg in self.history:
            role = "user" if isinstance(msg, HumanMessage) else "assistant"
            data.append({"role": role, "content": msg.content})
        
        with open(self.history_file, "w") as f:
            json.dump(data, f, indent=2)

    def _health_check(self):
        print(f"[*] Checking Ollama connectivity at {self.config['model_url']}...")
        try:
            # Simple check to see if service is up
            ollama_client = ollama.Client(host=self.config['model_url'])
            response = ollama_client.list()
            
            # Check if model exists
            model_name = self.config["model"]
            model_exists = False
            exact_model_name = None
            if hasattr(response, 'models'):
                for m in response.models:
                    # Check for exact match or exact match + :latest
                    if m.model == model_name or m.model == f"{model_name}:latest":
                        model_exists = True
                        exact_model_name = m.model
                        break
                    # Fallback: if we find a versioned tag and none was specified
                    elif ":" not in model_name and m.model.startswith(f"{model_name}:"):
                        model_exists = True
                        exact_model_name = m.model
                        break
            
            if not model_exists:
                if model_name == "alone-model":
                    print("[!] Custom model 'alone-model' not found. Self-healing/compilation triggered...")
                    # 1. Check if base model llama3.2:3b exists
                    base_model = "llama3.2:3b"
                    base_exists = False
                    for m in response.models:
                        if m.model == base_model or m.model == f"{base_model}:latest":
                            base_exists = True
                            break
                    if not base_exists:
                        print(f"[*] Base model '{base_model}' not found. Pulling it first...")
                        ollama_client.pull(base_model)
                        print(f"[+] Base model '{base_model}' pulled successfully.")
                    
                    # 2. Check if Modelfile exists, if not write it
                    modelfile_path = "Modelfile"
                    if not os.path.exists(modelfile_path):
                        if os.path.exists("../Modelfile"):
                            modelfile_path = "../Modelfile"
                        else:
                            with open(modelfile_path, "w") as f:
                                f.write("FROM llama3.2:3b\nPARAMETER num_gpu 20\nPARAMETER num_thread 6\n")
                    
                    # 3. Create the model
                    print("[*] Creating local model 'alone-model' from Modelfile...")
                    import subprocess
                    subprocess.run(["ollama", "create", "alone-model", "-f", modelfile_path], check=True)
                    print("[+] Custom 'alone-model' created successfully.")
                    self.config["model"] = "alone-model"
                    self.client.model = "alone-model"
                else:
                    print(f"[!] Model '{model_name}' not found. Attempting to pull...")
                    ollama_client.pull(model_name)
                    print(f"[+] Model '{model_name}' pulled successfully.")
            else:
                # Update the chat client with the exact model name found
                self.config["model"] = exact_model_name
                self.client.model = exact_model_name
                print(f"[+] Ollama online and model '{exact_model_name}' ready.")
                
        except Exception as e:
            print(f"[!] Error connecting to Ollama: {e}")
            print("Please ensure Ollama is running and accessible.")
            exit(1)

    def chat(self, user_message):
        # Append user message to history
        self.history.append(HumanMessage(content=user_message))
        
        # Trim history if it exceeds max_history (keep last N messages)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
            
        # Retrieve context from past sessions using ChromaDB semantic search
        from core import memory
        past_context = memory.retrieve_context(user_message, top_k=3)
        
        # Retrieve structured human memory context (profile, projects, goals, relationships)
        try:
            from core.human_memory import service as human_memory_service
            structured_context = human_memory_service.get_active_context_summary()
        except Exception as ex:
            print(f"[Brain Warning] Failed to import/retrieve structured memory: {ex}")
            structured_context = ""
        
        dynamic_system_prompt = self.system_prompt
        if structured_context:
            dynamic_system_prompt += f"\n\n{structured_context}"
        if past_context:
            dynamic_system_prompt += f"\n\nRelevant context from past sessions:\n{past_context}"
        
        # Prepare messages for LLM (Dynamic System Prompt + History)
        messages = [SystemMessage(content=dynamic_system_prompt)] + self.history
        
        try:
            response = self.client.invoke(messages)
            ai_content = response.content
            
            # Append AI response to history
            self.history.append(AIMessage(content=ai_content))
            
            # Trim history if it exceeds max_history (keep last N messages)
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]
            
            # Persist history
            self._save_history()
            
            # Save the newly completed exchange to persistent ChromaDB memory
            memory.add_memory("user", user_message)
            memory.add_memory("assistant", ai_content)
            
            return ai_content
        except Exception as e:
            return f"I apologize, Sir, but I encountered an error: {e}"
