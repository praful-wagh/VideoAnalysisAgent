# 🕵️‍♀️ Hercules Video Analysis Agent

An intelligent, model-agnostic monitoring agent designed to validate autonomous test runs. This tool automatically audits test executions by correlating the agent's **intended plan** with the **actual execution evidence** (video logs, DOM states, or visual descriptions) to detect deviations, failures, or skipped steps.


## ✨ Features

* **Stateful Orchestration:** Built on **LangGraph** to manage the complex workflow between log parsing, semantic analysis, and report generation.
* **Model Agnostic:** Plug-and-play support for major LLM providers. Switch easily between **Groq (Llama 3)**, **OpenAI (GPT-4o)**, and **Google (Gemini)** via configuration.
* **Semantic Verification:** Uses LLMs to "understand" context. Unlike simple keyword matching, it determines if an action (e.g., "Select Turtle Neck filter") actually occurred based on DOM evidence (e.g., "Filter option not found").
* **Robust Logging:** Handles complex nested JSON log structures and produces clear, human-readable Markdown reports.
* **Auto-Encoding Support:** Automatically handles UTF-8 character encoding to ensure emojis and special characters are preserved in output files on all operating systems (Windows/Linux/Mac).


## 📋 Prerequisites

* **Python 3.9** or higher
* An API Key for at least one supported provider (Groq, OpenAI, or Google Gemini).


## 🛠️ Installation

1.  **Clone the repository** (or download the source files):
    git clone https://github.com/test-zeus-ai/testzeus-hercules
    cd hercules-video-analysis

2.  **Install required dependencies:**
    pip install langgraph langchain langchain-openai langchain-google-genai langchain-groq python-dotenv



## 🔑 Configuration

The agent uses a `.env` file to manage sensitive credentials securely.

1.  Create a file named `.env` in the root directory of the project.
2.  Add the API key(s) for the model provider(s) you intend to use.

**Example `.env` file:**

```
# OPTION 1: Groq (Recommended for high-speed inference)
GROQ_API_KEY=gsk_your_actual_groq_key_here

# OPTION 2: OpenAI (GPT-4o)
OPENAI_API_KEY=sk-your_actual_openai_key_here

# OPTION 3: Google (Gemini)
GOOGLE_API_KEY=AIzaSy_your_actual_google_key_here

```

*Note: You only need to provide the key for the model you plan to use.*



## 🚀 How to Run

1. **Prepare your input data:**
Ensure your log file is named `agent_inner_logs.json` and is placed in the root directory of the project.
2. **Execute the agent:**
Run the Python script from your terminal:
```
python video_analysis_agent.py

```


3. **Switching Models:**
To change the model (e.g., from Groq to OpenAI), open `video_analysis_agent.py` and modify the `analyze_log_file` call at the bottom of the script:
```python
# Example: Switch to OpenAI
analyze_log_file(..., provider="openai", model="gpt-4o")

```


## 💾 Saving the Output

The agent is configured to **automatically save** the analysis results to a file.

* **Automatic Saving:** Upon successful execution, a file named `deviation_report.md` will be created (or overwritten) in the same directory.
* **Console Output:** The report content is also printed to the console for immediate review.
* **Encoding:** The file is saved using UTF-8 encoding to ensure checkmarks (✅) and warning icons (❌) are displayed correctly.


## 📊 Sample Inputs & Expected Outputs

### Sample Input (`agent_inner_logs.json`)

* **Plan Step:** `"7. Locate the Neck filter section and select the 'Turtle Neck' filter."`
* **Evidence Log:** `"The 'Neck' filter section contains only the 'Crew Neck' option. There is no 'Turtle Neck' filter option available..."`

### Expected Output (`deviation_report.md`)

The agent generates a Markdown table identifying the failure:

| Step Description | Result | Notes/Evidence |
| --- | --- | --- |
| Navigate to https://wrangler.in | ✅ **Observed** | Homepage loaded successfully; Search icon visible. |
| Click on Search icon | ✅ **Observed** | Search input field appeared with placeholder text. |
| Enter 'Rainbow sweater' | ✅ **Observed** | Search results page loaded with 2 items. |
| **Select 'Turtle Neck' filter** | ❌ **Deviation** | **Step Failed.** Evidence: "No 'Turtle Neck' filter option available... only 'Crew Neck' option is present." |
| Assert one product displayed | ⚠️ **Skipped** | Skipped due to previous critical failure. |


## 🧠 Architecture Overview

The solution utilizes a **LangGraph** workflow to process data in three distinct stages:

1. **Parser Node (`HerculesLogParser`)**:
* Ingests raw JSON logs.
* Separates the *Intended Plan* (Planner Agent thoughts) from the *Observed Evidence* (User/Browser logs).


2. **Analyst Node (`AnalysisEngine`)**:
* Constructs a prompt containing the Plan and the chronological Evidence.
* Invokes the LLM (Groq/OpenAI) to perform a semantic "diff," checking if every planned step is supported by evidence.


3. **Reporter Node**:
* Synthesizes the LLM's JSON analysis into a structured Markdown report table.




## 📁 Project Structure

VideoAnalysis/
├── video_analysis_agent.py    # Main application logic (LangGraph definition)
├── agent_inner_logs.json      # Input file (Test execution logs)
├── deviation_report.md        # Output file (Generated automatically)
├── .env                       # Environment variables (API Keys)
└── README.md                  # Project documentation

