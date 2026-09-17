import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

import tools

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
MAX_STEPS = 8

SYSTEM_PROMPT = """You are a teaching-demo agent for a PostgreSQL database that integrates
Fields of The World (FTW) summaries with national agricultural statistics.

Rules:
- Use tools to obtain evidence before answering data questions.
- Call get_database_schema when you need table/column names.
- Use search_metadata when the user asks what a dataset/field means or whether two values are comparable.
- Prefer compare_country_year for a single country/year FTW-vs-cropland comparison.
- For other database questions, use execute_sql.
- Never invent table names, columns, numbers, units, or dataset facts.
- Only read-only SQL is allowed.
- If a SQL query fails, inspect the error and try a corrected query.
- When comparing FTW field area with national statistics, mention that different sources may use different definitions.
- Keep the final answer concise and grounded in the tool output.
"""

SCHEMA_TOOL = types.FunctionDeclaration(
    name="get_database_schema",
    description="Return PostgreSQL tables, columns, primary keys, and foreign keys.",
    parameters=types.Schema(type="OBJECT", properties={}),
)

METADATA_TOOL = types.FunctionDeclaration(
    name="search_metadata",
    description="Search metadata describing FTW and agricultural statistics.",
    parameters=types.Schema(
        type="OBJECT",
        properties={
            "query": types.Schema(type="STRING", description="Keywords to search for."),
        },
        required=["query"],
    ),
)

SQL_TOOL = types.FunctionDeclaration(
    name="execute_sql",
    description="Run one read-only SELECT/CTE query against PostgreSQL.",
    parameters=types.Schema(
        type="OBJECT",
        properties={
            "sql": types.Schema(type="STRING", description="A single PostgreSQL SELECT or WITH query."),
        },
        required=["sql"],
    ),
)

COMPARE_TOOL = types.FunctionDeclaration(
    name="compare_country_year",
    description="Compare FTW field area and cropland statistics for one country code and year.",
    parameters=types.Schema(
        type="OBJECT",
        properties={
            "country_code": types.Schema(type="STRING", description="Country code stored in the database."),
            "year": types.Schema(type="INTEGER", description="Year to compare."),
        },
        required=["country_code", "year"],
    ),
)

TOOL_CONFIG = types.Tool(
    function_declarations=[SCHEMA_TOOL, METADATA_TOOL, SQL_TOOL, COMPARE_TOOL]
)


def run_tool(name, args):
    if name == "get_database_schema":
        return tools.get_database_schema()
    if name == "search_metadata":
        return tools.search_metadata(args.get("query", ""))
    if name == "execute_sql":
        return tools.execute_sql(args.get("sql", ""))
    if name == "compare_country_year":
        return tools.compare_country_year(
            args.get("country_code", ""), args.get("year", 0)
        )
    return f"ERROR: unknown tool {name}"


def call_model(client, contents, config, tries=4):
    for attempt in range(tries):
        try:
            return client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=config,
            )
        except genai.errors.ServerError:
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt)
        except genai.errors.ClientError as exc:
            if getattr(exc, "code", None) != 429 or attempt == tries - 1:
                raise
            time.sleep(2 ** attempt)


def ask(question, client=None, verbose=True):
    if client is None:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[TOOL_CONFIG],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    contents = [types.Content(role="user", parts=[types.Part(text=question)])]
    calls_made = 0
    sql_run = []
    start = time.time()

    for _ in range(MAX_STEPS):
        response = call_model(client, contents, config)
        calls_made += 1
        function_calls = response.function_calls

        if not function_calls:
            return {
                "answer": response.text,
                "requests": calls_made,
                "seconds": round(time.time() - start, 1),
                "sql": sql_run,
                "error": None,
            }

        contents.append(response.candidates[0].content)
        tool_response_parts = []

        for call in function_calls:
            args = dict(call.args) if call.args else {}
            if call.name == "execute_sql":
                sql = args.get("sql", "")
                sql_run.append(sql)
                if verbose:
                    print(f"\nSQL: {sql}")

            result = run_tool(call.name, args)
            if verbose:
                print(f"\nTOOL {call.name}:\n{result}\n")

            tool_response_parts.append(
                types.Part.from_function_response(
                    name=call.name,
                    response={"result": result},
                )
            )

        contents.append(types.Content(role="user", parts=tool_response_parts))

    return {
        "answer": None,
        "requests": calls_made,
        "seconds": round(time.time() - start, 1),
        "sql": sql_run,
        "error": f"stopped after {MAX_STEPS} tool/model steps",
    }
