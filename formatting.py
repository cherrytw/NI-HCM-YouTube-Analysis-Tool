# formatting.py
def format_transcript_preview(transcript, length=500):
    """Format transcript preview with proper line breaks and indentation"""
    words = transcript[:length].split()
    lines = []
    current_line = "   "

    for word in words:
        if len(current_line) + len(word) > 80:
            lines.append(current_line)
            current_line = "   " + word
        else:
            current_line += " " + word

    lines.append(current_line)
    return "\n".join(lines) + "..."
