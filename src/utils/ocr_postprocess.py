"""OCR Post-processing Utilities"""

def fix_word_boundaries(text: str) -> str:
    """Fix word boundary issues in OCR output"""
    if not text:
        return text
    text = text.replace('  ', ' ')
    text = text.replace('\n ', '\n')
    text = text.replace(' \n', '\n')
    return text.strip()


def calculate_space_ratio(text: str) -> float:
    """Calculate space-to-character ratio for quality assessment"""
    if not text:
        return 0.0
    spaces = text.count(' ')
    total = len(text)
    return spaces / max(total, 1)
