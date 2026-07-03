import re


class TextCleaner:
    """Utility service to clean and normalize raw extracted document text."""

    @staticmethod
    def clean(text: str) -> str:
        """Cleans and normalizes raw text extracted from documents.
        
        - Standardizes newlines to '\n'
        - Replaces multiple horizontal spaces/tabs with a single space
        - Collapses 3 or more consecutive newlines to a double newline
        - Strips whitespace from lines
        """
        if not text:
            return ""

        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Replace multiple consecutive spaces/tabs within a line with a single space
        text = re.sub(r"[ \t]+", " ", text)

        # Strip spaces from each line, but preserve newlines
        lines = [line.strip() for line in text.split("\n")]
        
        # Re-join lines
        text = "\n".join(lines)

        # Compress 3 or more consecutive newlines into a maximum of 2 (a blank line)
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()
