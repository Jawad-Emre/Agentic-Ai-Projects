from src.llm.client import get_llm

llm = get_llm()

response = llm.invoke("Reply with exactly one word: 'working'")

if isinstance(response.content, list):
    text_only = next(
        (block["text"] for block in response.content if isinstance(block, dict) and block.get("type") == "text"),
        str(response.content)
    )
else:
    text_only = response.content

print("Extracted text:", text_only)