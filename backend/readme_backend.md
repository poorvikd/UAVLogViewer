# UAVLogViewer Backend: Agentic AI System (app.py)

## Overview

This backend powers the UAVLogViewer's AI-driven chat interface for UAV telemetry log analysis. It implements a two-agent (agentic) architecture using OpenAI's GPT models, enabling users to ask natural language questions about UAV flight logs and receive concise, evidence-based answers. The system is designed for extensibility, robust error handling, and clear separation of concerns between data collection and reasoning.

---

## Architecture

### 1. Two-Agent System
- **Data-Collection Agent**: Determines exactly which telemetry values (atomic data points or summaries) are needed to answer the user's question. It plans and issues tool calls to fetch or summarize data.
- **Reasoning Agent**: Receives only the data collected by the first agent and produces a concise, factual answer, citing evidence and making recommendations if needed.

### 2. Tool-Driven Approach
- **flight_data_parser_tool**: Fetches a specific value or series from the nested telemetry data structure.
- **flight_data_summary_tool**: Computes a summary statistic (first, last, min, max, average, count_where, etc.) from a telemetry series.

---

## Simple Query Agentic Workflow Architecture

A "simple" query is one that can be answered using at most one or two atomic data points or summary statistics (e.g., "What was the maximum altitude?", "How many satellites were visible at takeoff?").

**Step-by-Step Workflow:**
1. **User Query**: The user submits a question via the `/api/chat` endpoint.
2. **Complexity Classification**: The system uses an LLM to classify the query as "simple".
3. **Agentic Planning**:
    - The Data-Collection Agent plans which single (or at most two) telemetry series or values are needed.
    - It issues tool calls to either `flight_data_parser_tool` (for a value/series) or `flight_data_summary_tool` (for a summary statistic).
    - The agent ensures no duplicate tool calls and justifies any second series if needed.
4. **Tool Execution**: The backend executes the tool calls, fetching the required data from the nested telemetry structure.
5. **Reasoning Agent**: Receives only the fetched data and produces a concise answer, including a bullet list of evidence and recommendations if anomalies are found.
6. **Response**: The answer and supporting evidence are returned to the frontend.

**Key Features:**
- Maximum of two tool calls per query.
- No redundant data fetching.
- Output is concise, factual, and evidence-based.

---

## Complex Query Agentic Workflow Architecture

A "complex" query requires multiple data points, sequence analysis, anomaly detection, or trend analysis (e.g., "Were there any mid-flight GPS dropouts?", "Summarize the battery voltage trend and flag anomalies.").

**Step-by-Step Workflow:**
1. **User Query**: The user submits a question via the `/api/chat` endpoint.
2. **Complexity Classification**: The system uses an LLM to classify the query as "complex".
3. **Agentic Planning (Iterative)**:
    - The Data-Collection Agent plans a sequence of tool calls, possibly in multiple rounds, to gather all necessary evidence.
    - It may use both `flight_data_parser_tool` and `flight_data_summary_tool` for different series, statistics, or conditional counts.
    - After each round of tool calls, the agent may re-plan based on the data received, issuing further tool calls as needed.
4. **Tool Execution**: The backend executes each batch of tool calls, returning results to the agent for further planning if required.
5. **Reasoning Agent**: Once all relevant data is collected, the Reasoning Agent produces a concise, multi-faceted answer, including a bullet list of evidence and recommendations for anomalies or trends.
6. **Response**: The answer and supporting evidence are returned to the frontend.

**Key Features:**
- Supports iterative, multi-step data collection.
- Handles sequence analysis, anomaly detection, and trend summarization.
- Output is structured, evidence-based, and may include recommendations for further investigation. 
---
## Data Flow

1. **User Query**: User sends a question via the `/api/chat` endpoint, along with parsed log data and schema info.
2. **Complexity Classification**: The system uses an LLM to classify the question as 'simple' (1–2 data points) or 'complex' (requires sequence analysis, anomaly detection, or multiple data points).
3. **Agentic Processing**:
   - **Simple**: The system plans and executes up to two tool calls, then answers directly.
   - **Complex**: The system iteratively plans and executes as many tool calls as needed, collecting all relevant data before reasoning.
4. **Tool Call Execution**: Each tool call is handled by Python functions that traverse the nested telemetry data and compute summaries as needed.
5. **Reasoning**: The reasoning agent receives only the collected data and produces a short, evidence-based answer, including a bullet list of evidence and recommendations if anomalies are found.
6. **Response**: The answer, along with metadata (timestamp, file info), is returned to the frontend.

---

## Key Components

### 1. Tool Schemas
- **flight_data_parser_tool_schema**: Defines the structure for extracting a value or series from the data.
- **flight_data_summary_tool_schema**: Defines the structure for computing a summary statistic from a series.

### 2. Tool Handlers
- **flight_data_parser_tool(keys_list, data)**: Traverses the nested data using the provided path (keys_list) and returns the value or series.
- **flight_data_summary_tool(keys_list, operation, data, comparison, threshold)**: Fetches the series and computes the requested summary (e.g., min, max, average, count_where).
- **handle_tool_calls(tool_calls, data)**: Executes a batch of tool calls, returning results in a format compatible with OpenAI's function-calling API.

### 3. Agentic Functions
- **handle_simple_question(question, data, file_information_str)**: Handles simple questions with at most two tool calls, ensuring no redundant data fetching.
- **handle_complex_question(question, data, file_information_str)**: Handles complex questions, iteratively collecting all necessary data before reasoning.
- **handle_chat_request(question, data, file_information_str)**: Orchestrates the process: classifies complexity, dispatches to the appropriate handler, and returns the final answer.

### 4. API Endpoint
- **/api/chat [POST]**: Main endpoint for chat-based queries. Accepts a JSON payload with `message` (user question) and `fileInfo` (parsed log data and schema). Returns a JSON response with the answer, timestamp, and file metadata.
- **/api/hello [GET]**: Simple health check endpoint.

---

## Error Handling
- All exceptions in `/api/chat` are logged with full tracebacks using Python's `traceback` module.
- Errors are returned as JSON with status `error` and the error message.
- Tool functions return structured error messages if data is missing, not iterable, or if required parameters are absent.

---

## Extensibility
- **Adding New Tools**: Define a new tool schema and handler, then add it to the `tools` list in agentic functions.
- **Customizing Agent Prompts**: System prompts for both agents are modular and can be extended for new reasoning styles or domains.
- **Schema Awareness**: The system dynamically adapts to the provided schema, making it robust to new log formats.


---

## File Structure
- `app.py`: Main backend logic, agentic orchestration, tool definitions, and API endpoints.
- `schema-info.json`: Schema definitions for available telemetry message types and fields.
- `data.json`: Example or working telemetry data (not required for production).
- `app.log`: Log file for backend operations and errors.

---

## Security & API Keys
- Requires an OpenAI API key set in the environment variable `OPENAI_API_KEY`.
- CORS is enabled for `http://localhost:8080` for local development.

---
## Run the script

You can run the backend locally without any containerization. Follow these steps:

### 1. Set Up a Python Virtual Environment

#### Using venv (standard library, recommended for most users):
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### Using conda (if you prefer Anaconda/Miniconda):
```bash
cd backend
conda create -n uavlogviewer python=3.10
conda activate uavlogviewer
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Create a .env File
Create a file named `.env` in the `backend/` directory with the following content:
```
OPENAI_API_KEY=sk-...your_openai_api_key...
```
Replace `sk-...your_openai_api_key...` with your actual OpenAI API key.

### 4. Run the Backend
```bash
python app.py
```

The backend will start on `http://127.0.0.1:5000` by default. Front-end assumes that the API runs on localhost and port 5000.

---

## References
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [UAVLogViewer Frontend](../src/)

---
