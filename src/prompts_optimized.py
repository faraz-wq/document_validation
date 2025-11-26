"""
Token-Optimized Prompts for Document Extraction
Uses plain text format instead of JSON to reduce token usage by 20-40%
"""

from src.config import Config

def get_extraction_prompt_for_format(context_instructions: str = "") -> str:
    """
    Get extraction prompt optimized for the configured output format

    Args:
        context_instructions: Optional context-specific instructions

    Returns:
        Formatted prompt string
    """
    # Only text format is supported now
    return get_text_extraction_prompt(context_instructions)


def get_text_extraction_prompt(context_instructions: str = "") -> str:
    """
    TOKEN-OPTIMIZED: Plain text extraction prompt (saves 20-40% tokens)

    Uses simple key-value format instead of JSON
    """
    prompt = """Extract ALL information from this document.

Rules:
- Extract ALL text, labels, values, headers, footers, tables, handwritten notes
- Use format: Field_Name: value
- One field per line
- For missing/illegible values use: Not specified
- Don't summarize - extract everything
- For tables, use nested structure with indentation

"""
    if context_instructions:
        prompt += f"{context_instructions}\n\n"

    prompt += """Output each field as:
Field_Name: value

Example:
Document_Title: Income Certificate
Applicant_Name: John Doe
Father_Name: Richard Doe
Date_of_Birth: 15/08/1990
"""
    return prompt





def get_page_prompt_for_format(page_num: int, context_instructions: str = "") -> str:
    """
    Get page-specific prompt optimized for the configured output format

    Args:
        page_num: Page number
        context_instructions: Optional context hints

    Returns:
        Formatted prompt string
    """
    # Only text format is supported now
    return get_page_text_prompt(page_num, context_instructions)


def get_page_text_prompt(page_num: int, context_instructions: str = "") -> str:
    """
    TOKEN-OPTIMIZED: Page extraction in plain text format
    """
    prompt = f"""Extract ALL data from page {page_num}.

"""
    if context_instructions:
        prompt += f"{context_instructions}\n\n"

    prompt += f"""Rules:
- Extract every visible field, text, signature, stamp, table cell
- Use format: Page_{page_num}_Field_Name: value
- One field per line
- For tables use indentation

Output each field as:
Page_{page_num}_Field_Name: value

Example:
Page_{page_num}_Title: Application Form
Page_{page_num}_Applicant_Name: John Doe
Page_{page_num}_Section_A_Field1: value1
  Page_{page_num}_Section_A_Field1_SubItem: subvalue
"""
    return prompt






