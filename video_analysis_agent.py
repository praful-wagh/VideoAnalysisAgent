import json
import os
import re
import sys
from typing import List, Dict, TypedDict, Any, Optional, Union
from enum import Enum
from dotenv import load_dotenv

# LangChain & LangGraph
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END

# --- 1. Configuration & Model Factory ---

class ModelProvider(Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    GROQ = "groq"

class LLMFactory:
    """Factory to create LLM instances based on provider configuration."""
    
    @staticmethod
    def create_llm(provider: ModelProvider, model_name: str = None, api_key: str = None):
        if provider == ModelProvider.OPENAI:
            return ChatOpenAI(
                model=model_name or "gpt-4o",
                api_key=api_key or os.getenv("OPENAI_API_KEY"),
                temperature=0
            )
        elif provider == ModelProvider.GEMINI:
            return ChatGoogleGenerativeAI(
                model=model_name or "gemini-1.5-pro",
                google_api_key=api_key or os.getenv("GOOGLE_API_KEY"),
                temperature=0
            )
        elif provider == ModelProvider.GROQ:
            return ChatGroq(
                model_name=model_name or "llama3-70b-8192",
                api_key=api_key or os.getenv("GROQ_API_KEY"),
                temperature=0
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

# --- 2. State Definition ---

class StepAnalysis(TypedDict):
    step: str
    status: str  # "Observed", "Deviation", "Skipped"
    evidence: str
    reasoning: str

class AgentState(TypedDict):
    raw_logs: Union[List[Dict], Dict]
    parsed_plan: List[str]
    parsed_evidence: List[Dict] 
    analysis_report: List[StepAnalysis]
    final_markdown: str
    
    # Config passed in state
    model_provider: str 
    model_name: str

# --- 3. Log Parsing Strategy ---

class BaseLogParser:
    def extract_plan(self, logs: Any) -> List[str]:
        raise NotImplementedError
    
    def extract_evidence(self, logs: Any) -> List[Dict]:
        raise NotImplementedError

class HerculesLogParser(BaseLogParser):
    """Specific parser for the Hercules agent_inner_logs.json format."""
    
    def extract_plan(self, logs: Any) -> List[str]:
        if isinstance(logs, dict) and 'planner_agent' in logs:
            target_logs = logs['planner_agent']
        elif isinstance(logs, list):
            target_logs = logs
        else:
            return []

        for entry in target_logs:
            if entry.get('name') == 'planner_agent' and isinstance(entry.get('content'), dict):
                plan_text = entry['content'].get('plan', '')
                if plan_text:
                    steps = [re.sub(r'^\d+\.\s*', '', line).strip() 
                             for line in plan_text.split('\n') if line.strip()]
                    return steps
        return []

    def extract_evidence(self, logs: Any) -> List[Dict]:
        if isinstance(logs, dict) and 'planner_agent' in logs:
            target_logs = logs['planner_agent']
        else:
            target_logs = logs if isinstance(logs, list) else []
            
        evidence = []
        for i, entry in enumerate(target_logs):
            if entry.get('name') == 'user':
                content = entry.get('content', '')
                if isinstance(content, dict):
                    desc = json.dumps(content)
                else:
                    desc = str(content)
                
                evidence.append({
                    "id": i,
                    "type": "observation",
                    "description": desc
                })
        return evidence

# --- 4. Graph Nodes ---

def parse_logs_node(state: AgentState):
    # Select parser (defaulting to Hercules for this assignment)
    parser = HerculesLogParser()
    plan = parser.extract_plan(state['raw_logs'])
    evidence = parser.extract_evidence(state['raw_logs'])
    return {"parsed_plan": plan, "parsed_evidence": evidence}

def analysis_node(state: AgentState):
    print(f"--- 🧠 Analyzing with {state.get('model_provider', 'openai').upper()} ---")
    
    provider = ModelProvider(state.get('model_provider', 'openai'))
    llm = LLMFactory.create_llm(provider, state.get('model_name'))

    plan = state['parsed_plan']
    evidence_text = "\n\n".join([f"[Log ID {e['id']}] {e['description'][:1500]}" for e in state['parsed_evidence']]) 

    prompt = f"""
    You are an Expert QA Video Analyst. Your task is to verify if a test agent executed its plan correctly based on the Execution Logs provided.
    
    The 'Execution Logs' act as the ground truth (visual evidence/DOM state).
    
    PLAN TO VERIFY:
    {json.dumps(plan, indent=2)}
    
    EXECUTION LOGS (EVIDENCE):
    {evidence_text}
    
    INSTRUCTIONS:
    1. For EACH step in the plan, determine if it was "Observed", a "Deviation", or "Skipped".
    2. "Observed": The log confirms the action happened.
    3. "Deviation": The log shows a failure, error, or missing element.
    4. "Skipped": Steps that were supposed to happen AFTER a Deviation/Failure.
    
    Return the result strictly as a JSON list of objects with keys: "step", "status", "evidence_snippet", "reasoning".
    Do not add markdown formatting.
    """

    response = llm.invoke([HumanMessage(content=prompt)])
    
    content = response.content.strip()
    if content.startswith("```json"): content = content[7:]
    if content.endswith("```"): content = content[:-3]
    
    try:
        analysis_result = json.loads(content)
    except json.JSONDecodeError:
        analysis_result = [{"step": "Error parsing LLM output", "status": "Deviation", "reasoning": content, "evidence": ""}]

    return {"analysis_report": analysis_result}

def reporting_node(state: AgentState):
    print("--- 📝 Generating Report ---")
    report = state['analysis_report']
    
    md = "# 🕵️‍♀️ Hercules Video Analysis Report\n\n"
    md += "| Step Description | Result | Notes/Evidence |\n"
    md += "| :--- | :--- | :--- |\n"
    
    for item in report:
        status_icon = "✅"
        if item['status'].lower() == "deviation": status_icon = "❌"
        if item['status'].lower() == "skipped": status_icon = "⚠️"
        
        safe_reasoning = item['reasoning'].replace("|", "-").replace("\n", " ")
        md += f"| {item['step']} | {status_icon} **{item['status']}** | {safe_reasoning} |\n"
        
    return {"final_markdown": md}

# --- 5. Graph Construction ---

def create_agent_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("parser", parse_logs_node)
    workflow.add_node("analyst", analysis_node)
    workflow.add_node("reporter", reporting_node)
    
    workflow.set_entry_point("parser")
    
    workflow.add_edge("parser", "analyst")
    workflow.add_edge("analyst", "reporter")
    workflow.add_edge("reporter", END)
    
    return workflow.compile()

# --- 6. Execution Helper ---

def analyze_log_file(file_path: str, output_file: str, provider: str = "openai", model: str = None):
    # Load File
    with open(file_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    # Run Graph
    app = create_agent_graph()
    inputs = {
        "raw_logs": raw_data,
        "model_provider": provider,
        "model_name": model
    }
    
    result = app.invoke(inputs)
    final_report = result['final_markdown']

    # --- SAVE TO FILE (Fixes Encoding Issue) ---
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(final_report)
        print(f"\n✅ Success! Report saved to: {output_file}")
    except Exception as e:
        print(f"\n❌ Error saving file: {e}")

    return final_report

# --- Usage Example ---
if __name__ == "__main__":
    load_dotenv()

    # Define output filename here
    OUTPUT_FILENAME = "deviation_report.md"

    try:
        analyze_log_file(
            file_path="agent_inner_logs.json", 
            output_file=OUTPUT_FILENAME,     # Pass the output filename
            provider="groq",                 # Change to "openai" or "gemini" as needed
            model="openai/gpt-oss-120b"
        )
    except Exception as e:
        print(f"Execution failed: {e}")