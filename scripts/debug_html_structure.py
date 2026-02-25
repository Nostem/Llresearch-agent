"""
Quick diagnostic: show the parent/sibling structure around the first
<h4 class="speaker"> in a saved session HTML file.

Usage:
    python scripts/debug_html_structure.py data/raw/session-001.html
"""
import sys
from pathlib import Path
from bs4 import BeautifulSoup

if len(sys.argv) < 2:
    print("Usage: python scripts/debug_html_structure.py <html_file>")
    sys.exit(1)

html = Path(sys.argv[1]).read_text(encoding="utf-8")
soup = BeautifulSoup(html, "lxml")

h4s = soup.find_all("h4", class_="speaker")
print(f"Found {len(h4s)} <h4 class='speaker'> elements\n")

if not h4s:
    print("NO H4 SPEAKER ELEMENTS FOUND — check HTML parser / file content")
    sys.exit(1)

h4 = h4s[0]
parent = h4.parent
print(f"Parent tag: <{parent.name} class='{parent.get('class', [])}' id='{parent.get('id', '')}'>\n")

print("=== h4.next_siblings (first 10) ===")
count = 0
for s in h4.next_siblings:
    if count >= 10:
        print("  ... (stopped at 10)")
        break
    tag_name = getattr(s, "name", None)
    if tag_name:
        cls = s.get("class", [])
        text_preview = s.get_text(strip=True)[:80]
        print(f"  <{tag_name} class={cls}> {text_preview!r}")
        count += 1

print("\n=== Parent's children (all, up to 20) ===")
count = 0
for child in parent.children:
    if count >= 20:
        print("  ... (stopped at 20)")
        break
    tag_name = getattr(child, "name", None)
    if tag_name:
        cls = child.get("class", [])
        text_preview = child.get_text(strip=True)[:80]
        print(f"  <{tag_name} class={cls}> {text_preview!r}")
        count += 1
