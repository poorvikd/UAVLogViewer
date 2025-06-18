from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from datetime import datetime
import time
import json
import os
import traceback
from openai import OpenAI
app = Flask(__name__)
CORS(app, origins=["http://localhost:8080"], supports_credentials=True)

# Configure logging to file
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Common prompt components
SIMPLE_QUESTION_TOOL_INSTRUCTIONS = """
You have two tools:

• **flight_data_parser_tool** – fetches an entire telemetry series or a scalar value.
   ▸ Argument: keys_list (e.g. ['GPS[0]', 'Status'])

• **flight_data_summary_tool** – computes a simple summary from a telemetry series.
   ▸ Arguments:
       keys_list : path to the series (e.g. ['GPS[0]', 'time_boot_ms'])
       operation : 'first' | 'last' | 'min' | 'max' | 'average' |
                   'first_index_where' | 'count_where'
       comparison, threshold : only for *_where operations

**When to use each tool:**

❗ **Use flight_data_summary_tool directly** for:
   • Duration calculations: get 'first' and 'last' timestamps from time series
   • Statistical summaries: min, max, average of any series
   • Count operations: count_where with conditions
   • Any calculation that needs just the first/last/min/max values

❗ **Use flight_data_parser_tool** only for:
   • When you need the full series for complex analysis


➡️ **One tool call = one atomic path.** Never chain multiple fields in the same call.

   ⛔ Wrong : ['GPS[0]', 'time_boot_ms', 'Status']
   ✅ Right : ['GPS[0]', 'time_boot_ms']   (summary call #1)
             ['GPS[0]', 'Status']         (parser call #2)

❌ No prose, explanations, or partial answers before the tool calls.

✅ After tool responses arrive, compose a short answer (≤ 4 sentences) followed by
   an "Evidence:" bullet list citing the fetched values or timestamps. Base every
   claim strictly on the returned data; if information is missing, state that
   politely and suggest what additional data is required.
"""

flight_data_parser_tool_schema = {
    "name": "flight_data_parser_tool",
    "description": "Extracts a specific value from parsed UAV flight data using a sequence of nested keys. Used to locate telemetry values (e.g., altitude, GPS fix, etc.) from structured messages.",
    "parameters": {
        "type": "object",
        "properties": {
            "keys_list": {
                "type": "object",
                "description": "A dictionary that represents the path to the desired value in the data. Each key leads to the next nested level. For example: {\"message_type\": \"POS\", \"field\": \"Alt\"}"
            },
        },
        "required": ["keys_list"]
    }
}
flight_data_summary_tool_schema = {
    "name": "flight_data_summary_tool",
    "description": (
        "Returns a summary statistic computed from a telemetry series that "
        "has already been fetched via flight_data_parser_tool."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "keys_list": {
                "type": "array",
                "description": (
                    "Path to the series you want to summarise, e.g. "
                    "['GPS[0]', 'Status'] or ['POS', 'Alt']"
                ),
                "items": {"type": ["string", "integer"]}
            },
            "operation": {
                "type": "string",
                "description": (
                    "Summary to compute. "
                    "Allowed: 'first', 'last', 'min', 'max', 'average', "
                    "'first_index_where', 'count_where'"
                )
            },
            "comparison": {
                "type": "string",
                "description": (
                    "Comparison operator for *_where operations "
                    "('==', '!=', '<', '<=', '>', '>=')."
                ),
                "enum": ["==", "!=", "<", "<=", ">", ">="]
            },
            "threshold": {
                "type": ["number", "integer", "string", "boolean"],
                "description": "Value to compare against in *_where operations"
            }
        },
        "required": ["keys_list", "operation"]
    }
}

def _apply_comparison(value, comparison, threshold):
    if comparison == "==":  return value == threshold
    if comparison == "!=":  return value != threshold
    if comparison == "<":   return value < threshold
    if comparison == "<=":  return value <= threshold
    if comparison == ">":   return value > threshold
    if comparison == ">=":  return value >= threshold
    return False


def flight_data_summary_tool(keys_list, operation, data, comparison=None, threshold=None):
    """
    Summarise a telemetry series already present in `data`.
    """
    series = flight_data_parser_tool(keys_list, data)

    # Guard-rails: series must be list-like or dict of lists
    if series is None or series == {}:
        logger.info(f"Series not found for {keys_list}")
        return {"error": "series_not_found"}

    # Convert dict-of-lists → list (we only need values)
    if isinstance(series, dict):
        # assume dict keyed by indices or timestamps → list(values)
        series = list(series.values())

    # From here `series` should be indexable
    if not isinstance(series, (list, tuple)):
        logger.info(f"Series {keys_list} not iterable")
        return {"error": "not_iterable"}

    result = None
    if operation == "first":
        result = series[0]
    elif operation == "last":
        result = series[-1]
    elif operation == "min":
        result = min(series)
    elif operation == "max":
        result = max(series)
    elif operation == "average":
        result = sum(series) / len(series) if series else None
    elif operation == "first_index_where":
        if comparison is None or threshold is None:
            return {"error": "comparison_or_threshold_missing"}
        for idx, val in enumerate(series):
            if _apply_comparison(val, comparison, threshold):
                result = {"index": idx, "value": val}
                break
        if result is None:
            result = {"index": None, "value": None}
    elif operation == "count_where":
        if comparison is None or threshold is None:
            return {"error": "comparison_or_threshold_missing"}
        count = sum(_apply_comparison(v, comparison, threshold) for v in series)
        result = {"count": count}
    else:
        result = {"error": "unknown_operation"}

    logger.info(f"Summary {operation} computed for {keys_list} with result {result}")
    return result


def flight_data_parser_tool(keys_list, data):
    #"keys_list":["GPS[0]","Status"]
    # logging data retrieved to a file log.txt
    parsed = False
    print(keys_list)
    for key in keys_list:
        if type(key) == int:
            data = list(data.values())
            data = data[key]
            parsed = True
            continue
        if key in data:
            data = data[key]
            parsed = True

    if parsed:
        logger.info(f"Data retrieved for keys {keys_list}")
        return data
    else:
        logger.info(f"Data not found for keys {keys_list}")
        return {}

def handle_tool_calls(tool_calls, data):
    results = []
    for tc in tool_calls:
        tool_name = tc.function.name
        print("Tool name: ", tool_name)
        args = json.loads(tc.function.arguments)

        if tool_name == "flight_data_parser_tool":
            extracted = flight_data_parser_tool(args.get("keys_list"), data)
            content = extracted if extracted != {} else \
                f"Data not found for keys {args.get('keys_list')}"
            results.append({
                "role": "tool",
                "content": json.dumps(content),
                "tool_call_id": tc.id,
                "keys_list": args.get("keys_list"),
                "operation": "parser"
            })

        elif tool_name == "flight_data_summary_tool":
            summary = flight_data_summary_tool(
                args.get("keys_list"),
                args.get("operation"),
                data,
                args.get("comparison"),
                args.get("threshold")
            )
            results.append({
                "role": "tool",
                "content": json.dumps(summary),
                "tool_call_id": tc.id,
                "keys_list": args.get("keys_list"),
                "operation": args.get("operation")
            })

    return results
    
def handle_complex_question(question, data, file_information_str):
    openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    stage1_messages = [
        {
            "role": "system",
            "content": f"""
            You are the **Data‑Collection Agent** for a two‑agent UAV‑log analysis system.
            Your objective is to decide exactly **which atomic telemetry values** the reasoning
            agent will need to answer the user's question. Think like a scientist preparing an
            experiment: gather **minimal yet sufficient** evidence.

            The telemetry is provided as nested dicts whose top‑level keys are message types.
            Available schema:
            {file_information_str}

            {SIMPLE_QUESTION_TOOL_INSTRUCTIONS}

            If the question requires a time series analysis, you must use the summary tool.
            """
        },
        {"role": "user", "content": question}
    ]

    tools = [
        {"type": "function", "function": flight_data_parser_tool_schema},
        {"type": "function", "function": flight_data_summary_tool_schema}
    ]

    collected_data = {}
    done = False
    while not done:
        response = openai.chat.completions.create(
            model="gpt-4.1",
            messages=stage1_messages,
            tools=tools
        )
        finish_reason = response.choices[0].finish_reason

        if finish_reason == "tool_calls":
            message = response.choices[0].message
            tool_calls = message.tool_calls
            results = handle_tool_calls(tool_calls, data)
            stage1_messages.append(message)
            stage1_messages.extend(results)

            for result in results:
                try:
                    content = json.loads(result["content"])
                    collected_data[f"{result['operation']} - {result['keys_list']}"] = content
                except:
                    collected_data[f"{result['operation']} - {result['keys_list']}"] = result["content"]
            time.sleep(1)
        else:
            done = True

    stage2_messages = [
        {
            "role": "system",
            "content": """
            You are the **Reasoning Agent** for UAV flight‑log analysis. Use
            ONLY the data supplied by the collection agent (no new tool
            calls). Provide a concise, factual answer to the user. Use the below schema to understand the data you recieve from the summary tool.

            ──────────────  SCHEMA  ──────────────
            {file_information_str}

            **Output format**:
                1. One short paragraph (≤ 2 sentences) stating the conclusion.
                2. A bullet list of key evidence lines – each references the
                    exact message‑type/field and value you used.
                3. If anomalies are present, include a 'Recommendations' line.
                4. Do not include tool call ids in the output. Instead, describe the tool call.

            Base your reasoning on patterns / trends / thresholds rather than
            hard‑coded rules. If data is insufficient, state that clearly. Do not include tool call ids in the output. Instead, describe the tool call.
            """
        },
        {
            "role": "user",
            "content": f"Question: {question}\n\nCollected Data: {json.dumps(collected_data, indent=2)}"
        }
    ]

    final_response = openai.chat.completions.create(
        model="gpt-4.1",
        messages=stage2_messages
    )

    return final_response.choices[0].message.content

def handle_simple_question(question, data, file_information_str):
    messages = [
        {
            "role": "system",
            "content": f"""
            You are a UAV-telemetry analyst. The flight data are parsed into nested
            dictionaries; valid paths are listed below. To answer the user's question
            you must plan which *single* telemetry series (or two, if comparison is
            explicitly required).

            ──────────────  SCHEMA  ──────────────
            {file_information_str}

            {SIMPLE_QUESTION_TOOL_INSTRUCTIONS}

            Additional guard-rails:
            • ⚡  **No duplicate parser calls.** If you've already fetched a path,
                reuse it rather than calling the tool again.
            • 🪝  *Justify* any second series you fetch: only request both GPS and POS
                altitude if the user's question requires comparing them (say so in your
                reasoning).
            • 🚦  Never fetch more than two distinct series for a simple question.

            Provide a concise, factual answer to the user.

            **Output format**:
            1. One short paragraph (≤ 2 sentences) stating the conclusion.
            2. A bullet list of key evidence lines – each references the
                exact message‑type/field and value you used.
            3. If anomalies are present, include a 'Recommendations' line.
            4. Do not include the tool calls in the output, especially the tool call ids. Instead, describe the tool call.

            Base your reasoning on patterns / trends / thresholds rather than
            hard‑coded rules. If data is insufficient, state that clearly.
            """
        },
        {"role": "user", "content": question}
    ]

    openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    tools = [
        {"type": "function", "function": flight_data_parser_tool_schema},
        {"type": "function", "function": flight_data_summary_tool_schema},
    ]

    fetched_paths = set() 
    done = False
    answer = ""

    while not done:
        response = openai.chat.completions.create(
            model="gpt-4.1",
            messages=messages,
            tools=tools
        )

        choice = response.choices[0]
        finish_reason = choice.finish_reason

        if finish_reason == "tool_calls":
            msg = choice.message
            new_calls = []
            for tc in msg.tool_calls:
                if tc.function.name == "flight_data_parser_tool":
                    args = json.loads(tc.function.arguments)
                    path_tuple = tuple(args.get("keys_list", []))
                    if path_tuple in fetched_paths:
                        continue
                    fetched_paths.add(path_tuple)
                    new_calls.append(tc)
                else:
                    new_calls.append(tc)

            msg.tool_calls = new_calls  # keep only unique parser calls
            results = handle_tool_calls(msg.tool_calls, data)
            messages.append(msg)
            messages.extend(results)
            time.sleep(1)
        else:
            answer = choice.message.content
            done = True

    return answer

def handle_chat_request(question, data, file_information_str):
    openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Stage 0: Let the LLM decide complexity
    classification_messages = [
        {
            "role": "system",
            "content": f"""
            You are an expert UAV log assistant. Given a user's question about UAV flight data, classify whether the question is:
            - 'simple': can be answered using 1–2 data points (e.g., altitude, satellite count, flight duration using first/last timestamps) or without any data points.
            - 'complex': requires multiple data points, sequence analysis, or anomaly detection (e.g., identifying mid-flight issues, summaries, comparisons, trend analysis). Questions that need time series analysis beyond simple first/last values are complex.

            Data points are the values of the keys in the schema.
            {file_information_str}

            Respond with a single word: "simple" or "complex" only.
            """
        },
        {"role": "user", "content": question}
    ]

    classification_response = openai.chat.completions.create(
        model="gpt-4.1",
        messages=classification_messages
    )

    complexity = classification_response.choices[0].message.content.strip().lower()

    print("Complexity: ", complexity)
    time.sleep(1)
    if complexity == "simple":
        return handle_simple_question(question, data, file_information_str)
    else:
        return handle_complex_question(question, data, file_information_str)

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message')
        file_info = data.get('fileInfo', {})
        
        file_information = {}
        with open('schema-info.json', 'r') as f:
            schema_info = json.load(f)
        for message_type in file_info.get('messages', {}):
            file_information[message_type] = schema_info.get(message_type, list(file_info['messages'][message_type].keys()))
        
                                    
        file_information_str = json.dumps(file_information)
        data = file_info.get('messages')
        
        # Check if this is a complex question that requires multiple data points
        answer = handle_chat_request(message, data, file_information_str)
            
        
        response = {
            "status": "success",
            "message": f"{answer}. ",
            "timestamp": datetime.now().isoformat(),
            "fileInfo": {
                "name": file_info.get('name'),
                "type": file_info.get('type'),
                "messageCount": sum(len(msgs) for msgs in file_info.get('messages', {}).values()),
                "messageTypes": list(file_info.get('messages', {}).keys())
            }
        }
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        print(traceback.format_exc())
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    

@app.route('/api/hello', methods=['GET'])
def hello():
    return jsonify({"message": "Hello from Flask!", "status": "success"})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True) 
