import re
from html import unescape
from html.parser import HTMLParser
from typing import Dict, List, Tuple


class SafeMarkdownHTMLParser(HTMLParser):
    """
    Sanitizing HTML parser that strips scripts/styles/ads
    and formats readable content as Markdown.
    """

    IGNORABLE_TAGS = {
        "script",
        "style",
        "svg",
        "nav",
        "footer",
        "header",
        "aside",
        "iframe",
        "noscript",
        "form",
        "button",
    }

    def __init__(self) -> None:
        super().__init__()
        self.title: str = ""
        self.in_title: bool = False
        self.ignore_depth: int = 0
        self.output_parts: List[str] = []
        self._current_tag: str = ""

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str]]) -> None:
        tag_lower = tag.lower()
        self._current_tag = tag_lower

        if tag_lower in self.IGNORABLE_TAGS:
            self.ignore_depth += 1
            return

        if self.ignore_depth > 0:
            return

        if tag_lower == "title":
            self.in_title = True
        elif tag_lower in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag_lower[1])
            self.output_parts.append(f"\n\n{'#' * level} ")
        elif tag_lower == "p":
            self.output_parts.append("\n\n")
        elif tag_lower == "br":
            self.output_parts.append("\n")
        elif tag_lower == "li":
            self.output_parts.append("\n- ")
        elif tag_lower == "blockquote":
            self.output_parts.append("\n> ")
        elif tag_lower == "code":
            self.output_parts.append(" `")

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in self.IGNORABLE_TAGS:
            self.ignore_depth = max(0, self.ignore_depth - 1)
            return

        if self.ignore_depth > 0:
            return

        if tag_lower == "title":
            self.in_title = False
        elif tag_lower == "code":
            self.output_parts.append("` ")
        elif tag_lower in ("p", "div", "section", "article"):
            self.output_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title += data
            return

        if self.ignore_depth > 0:
            return

        text = unescape(data)
        if text.strip():
            self.output_parts.append(text)


def extract_clean_markdown(html_content: str) -> Dict[str, str]:
    """
    Parses untrusted HTML, strips dangerous tags, and outputs clean title, snippet, and markdown.
    """
    parser = SafeMarkdownHTMLParser()
    try:
        parser.feed(html_content)
        parser.close()
    except Exception:
        pass

    raw_markdown = "".join(parser.output_parts)
    # Normalize multiple line breaks and spaces
    cleaned = re.sub(r"\n{3,}", "\n\n", raw_markdown).strip()

    title = parser.title.strip() or "Web Source"
    # Create short snippet
    snippet = cleaned[:240].replace("\n", " ").strip()
    if len(cleaned) > 240:
        snippet += "..."

    return {
        "title": title,
        "content_markdown": cleaned,
        "snippet": snippet,
    }
