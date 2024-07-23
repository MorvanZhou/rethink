import json
import re
from typing import Dict

JSON_PTN = re.compile(
    r"^{\s*?\"(.+?)\":\s*?\"(.+?)\",\s*?\"(.+?)\":\s*?\"(.+?)\"\s*?,\s*?\"(.+?)\":\s*?\"(.+?)\"\s*?}",
    re.DOTALL | re.MULTILINE)
IMG_PTN = re.compile(r"!\[.*?\]\(.+?\)")
LINK_PTN = re.compile(r"\[(.*?)]\(.+?\)")


def parse_json_pattern(text: str) -> Dict[str, str]:
    def get_title_content(m):
        k1, v1, k2, v2, k3, v3 = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)
        v1 = v1.replace("\n", "\\n")
        v2 = v2.replace("\n", "\\n")
        v3 = v3.replace("\n", "\\n")
        d = json.loads(f'{{"{k1}": "{v1}", "{k2}": "{v2}", "{k3}": "{v3}"}}')
        return d

    m = JSON_PTN.search(text)
    if m:
        return get_title_content(m)
    oneline = text.replace("\n", "\\n")
    raise ValueError(f"Invalid JSON pattern: {oneline}")


def remove_links(text: str) -> str:
    t_ = IMG_PTN.sub("", text)
    t_ = LINK_PTN.sub(r"\1", t_)
    return t_
