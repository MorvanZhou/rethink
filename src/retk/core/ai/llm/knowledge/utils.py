import json
import re
from typing import Tuple

JSON_PTN = re.compile(r"^{\s*?\"title\":\s?\"(.+?)\",\s*?\"content\":\s?\"(.+?)\"\s*?}", re.DOTALL | re.MULTILINE)
IMG_PTN = re.compile(r"!\[.*?\]\(.+?\)")
LINK_PTN = re.compile(r"\[(.*?)]\(.+?\)")


def parse_json_pattern(text: str) -> Tuple[str, str]:
    m = JSON_PTN.search(text)
    if m:
        title, content = m.group(1), m.group(2)
        title = title.replace("\n", "\\n")
        content = content.replace("\n", "\\n")
        d = json.loads(f'{{"title": "{title}", "content": "{content}"}}')
        return d["title"], d["content"]
    raise ValueError(f"Invalid JSON pattern: {text}")


def remove_links(text: str) -> str:
    t_ = IMG_PTN.sub("", text)
    t_ = LINK_PTN.sub(r"\1", t_)
    return t_
