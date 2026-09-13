# test_tool_calling.py
from langchain_core.tools import tool
from src.llm.client import get_llm

@tool
def sample_tool(reason: str) -> str:
    """A test tool. Call this if you want to test tool calling."""
    return f"Tool called with: {reason}"

models_to_test = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemma-4-31b-it",
    "gemma-4-26b-a4b-it",
]

for model_name in models_to_test:
    try:
        llm = get_llm(model_name=model_name)
        llm_with_tools = llm.bind_tools([sample_tool])
        response = llm_with_tools.invoke("Please call sample_tool with reason='testing'")
        
        if response.tool_calls:
            print(f"✅ {model_name}: Tool calling WORKS — {response.tool_calls}")
        else:
            print(f"⚠️ {model_name}: No error, but no tool call made — response: {response.content[:100]}")
    except Exception as e:
        print(f"❌ {model_name}: FAILED — {str(e)[:150]}")