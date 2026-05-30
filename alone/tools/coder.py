import os
import subprocess
import yaml
from langchain_ollama import ChatOllama
from langchain.tools import tool

def _get_llm():
    # Load config to get model and url
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config.yaml")
    if not os.path.exists(config_path):
        if os.path.exists("config.yaml"):
            config_path = "config.yaml"
        elif os.path.exists("../config.yaml"):
            config_path = "../config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return ChatOllama(model=config["model"], base_url=config["model_url"], keep_alive="5m")

@tool
def write_code(input_str: str) -> str:
    """Generates Python code based on instructions. Input should be 'filename, instructions'."""
    try:
        if "," not in input_str:
            return "Error: Input must be in 'filename, instructions' format."
        
        filename, instructions = input_str.split(",", 1)
        filename = filename.strip().strip("'\"")
        instructions = instructions.strip()
        
        llm = _get_llm()
        prompt = (
            f"Generate only the Python code for the following task: {instructions}. "
            "Do not include any explanation, markdown formatting, or triple backticks. "
            "Just the code."
        )
        response = llm.invoke(prompt)
        code = response.content.strip()
        
        # Remove backticks if the LLM ignored instructions
        if code.startswith("```"):
            lines = code.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            code = "\n".join(lines).strip()

        save_path = os.path.join("data", "generated_code", filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        with open(save_path, "w") as f:
            f.write(code)
        
        return f"Code generated and saved to {save_path}:\n---\n{code}\n---"
    except Exception as e:
        return f"Failed to generate code: {e}"

@tool
def run_code(filepath: str) -> str:
    """Runs a Python file and returns the output."""
    try:
        # Check if it's in data/generated_code/ or absolute
        if not os.path.exists(filepath):
            test_path = os.path.join("data", "generated_code", filepath)
            if os.path.exists(test_path):
                filepath = test_path
            else:
                return f"File not found: {filepath}"

        result = subprocess.run(["python", filepath], capture_output=True, text=True)
        return f"Execution Output:\n{result.stdout}\nErrors (if any):\n{result.stderr}"
    except Exception as e:
        return f"Failed to run code: {e}"
