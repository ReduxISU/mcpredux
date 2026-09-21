def text_of(result) -> str:
    """Concatenate the text content blocks of a CallToolResult."""
    return "".join(c.text for c in result.content if c.type == "text")
