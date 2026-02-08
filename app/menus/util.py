from html.parser import HTMLParser
import os
import re
import textwrap
from shutil import get_terminal_size

from app.service.config import load_config

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")

ANSI_CODES = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "cyan": "\033[36m",
    "green": "\033[32m",
    "red": "\033[31m",
    "yellow": "\033[33m",
    "magenta": "\033[35m",
}

def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE_RE.sub("", text)

def style_text(text: str, color: str | None = None, *, bold: bool = False, dim: bool = False) -> str:
    if os.getenv("NO_COLOR"):
        return text

    styles = []
    if bold:
        styles.append(ANSI_CODES["bold"])
    if dim:
        styles.append(ANSI_CODES["dim"])
    if color:
        styles.append(ANSI_CODES.get(color, ""))

    return f"{''.join(styles)}{text}{ANSI_CODES['reset']}" if styles else text

def format_status(text: str, *, success: bool = True) -> str:
    return style_text(text, "green" if success else "red", bold=True)

def format_price(value: int | float | str, currency: str = "Rp") -> str:
    return style_text(f"{currency} {value}", "yellow", bold=True)

def render_header(title: str, width: int, subtitle: str | None = None, meta_lines: list[str] | None = None) -> str:
    separator = "=" * width
    lines = [separator]
    lines.append(style_text(title, "cyan", bold=True).center(width))
    if subtitle:
        lines.append(style_text(subtitle, dim=True).center(width))
    if meta_lines:
        for line in meta_lines:
            lines.append(line.center(width))
    lines.append(separator)
    return "\n".join(lines)

def render_table(
    headers: list[str],
    rows: list[list[str]],
    *,
    column_spacing: int = 2,
    separator_char: str = "-",
) -> str:
    columns = len(headers)
    col_widths = [len(strip_ansi(header)) for header in headers]
    for row in rows:
        for idx in range(columns):
            cell = row[idx] if idx < len(row) else ""
            col_widths[idx] = max(col_widths[idx], len(strip_ansi(str(cell))))

    spacer = " " * column_spacing
    header_line = spacer.join(
        header.ljust(col_widths[idx]) for idx, header in enumerate(headers)
    )
    separator = separator_char * len(strip_ansi(header_line))
    body_lines = []
    for row in rows:
        cells = []
        for idx in range(columns):
            cell = row[idx] if idx < len(row) else ""
            cell_text = str(cell)
            cells.append(cell_text.ljust(col_widths[idx] + (len(cell_text) - len(strip_ansi(cell_text)))))
        body_lines.append(spacer.join(cells))

    return "\n".join([header_line, separator, *body_lines])

def clear_screen():
    if os.getenv("MYXL_CLI_DEBUG") == "1":
        print("Clearing screen...")
    os.system('cls' if os.name == 'nt' else 'clear')
    config = load_config()
    if not config.get("show_banner", True):
        return

    terminal_width = get_terminal_size(fallback=(80, 24)).columns
    compact_banner = r"""
      __  __ __  ____ __
     / / / // / / __// /
    / /_/ // / / /_ / / 
    \__, //_/ /___//_/  
   /____/   MYXL CLI    
"""

    ascii_art = r"""
            _____                    _____          
           /\    \                  /\    \         
          /::\____\                /::\    \        
         /::::|   |               /::::\    \       
        /:::::|   |              /::::::\    \      
       /::::::|   |             /:::/\:::\    \     
      /:::/|::|   |            /:::/__\:::\    \    
     /:::/ |::|   |           /::::\   \:::\    \   
    /:::/  |::|___|______    /::::::\   \:::\    \  
   /:::/   |::::::::\    \  /:::/\:::\   \:::\    \ 
  /:::/    |:::::::::\____\/:::/__\:::\   \:::\____\
  \::/    / ~~~~~/:::/    /\:::\   \:::\   \::/    /
   \/____/      /:::/    /  \:::\   \:::\   \/____/ 
               /:::/    /    \:::\   \:::\    \     
              /:::/    /      \:::\   \:::\____\    
             /:::/    /        \:::\   \::/    /    
            /:::/    /          \:::\   \/____/     
           /:::/    /            \:::\    \         
          /:::/    /              \:::\____\        
          \::/    /                \::/    /        
           \/____/                  \/____/         
"""

    if terminal_width < 60:
        print("MYXL CLI")
    elif terminal_width < 90:
        print(compact_banner)
    else:
        print(ascii_art)

def pause():
    input("\nPress enter to continue...")

class HTMLToText(HTMLParser):
    def __init__(self, width=80):
        super().__init__()
        self.width = width
        self.result = []
        self.in_li = False

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            self.in_li = True
        elif tag == "br":
            self.result.append("\n")

    def handle_endtag(self, tag):
        if tag == "li":
            self.in_li = False
            self.result.append("\n")

    def handle_data(self, data):
        text = data.strip()
        if text:
            if self.in_li:
                self.result.append(f"- {text}")
            else:
                self.result.append(text)

    def get_text(self):
        # Join and clean multiple newlines
        text = "".join(self.result)
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
        # Wrap lines nicely
        return "\n".join(textwrap.wrap(text, width=self.width, replace_whitespace=False))

def display_html(html_text, width=80):
    parser = HTMLToText(width=width)
    parser.feed(html_text)
    return parser.get_text()

def format_quota_byte(quota_byte: int) -> str:
    GB = 1024 ** 3 
    MB = 1024 ** 2
    KB = 1024

    if quota_byte >= GB:
        return f"{quota_byte / GB:.2f} GB"
    elif quota_byte >= MB:
        return f"{quota_byte / MB:.2f} MB"
    elif quota_byte >= KB:
        return f"{quota_byte / KB:.2f} KB"
    else:
        return f"{quota_byte} B"
