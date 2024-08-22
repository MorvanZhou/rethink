import os
import re
from html.parser import HTMLParser
from io import StringIO
from typing import Tuple

from markdown import Markdown

from retk import regex


class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()

    def handle_data(self, d):
        self.text.write(d)

    def get_data(self):
        return self.text.getvalue()


def strip_html_tags(html: str) -> str:
    s = HTMLStripper()
    s.feed(html[:1000])
    return s.get_data()


def __unmark_element(element, stream=None):
    if stream is None:
        stream = StringIO()
    if element.text:
        stream.write(element.text)
    for sub in element:
        __unmark_element(sub, stream)
    if element.tail:
        stream.write(element.tail)
    return stream.getvalue()


# patching Markdown
Markdown.output_formats["plain"] = __unmark_element
__md = Markdown(output_format="plain")
__md.stripTopLevelTags = False
__md_html = Markdown(
    output_format="html",
)
with open(os.path.join(os.path.dirname(__file__), "markdown.css"), "r") as css_file:
    __css = css_file.read()

__markdown_html_template = """
<!DOCTYPE html>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
{css}
.markdown-body {{
    box-sizing: border-box;
    min-width: 200px;
    max-width: 980px;
    margin: 0 auto;
    padding: 45px;
}}

@media (max-width: 767px) {{
    .markdown-body {{
        padding: 15px;
    }}
}}
</style>
<body class="markdown-body">
{html}
</body>
</html>
"""


def md2txt(md: str) -> str:
    for found in list(regex.MD_CODE.finditer(md))[::-1]:
        span = found.span()
        code = found.group(1)
        md = f"{md[: span[0]]}{code}{md[span[1]:]}"
    return __md.convert(md)


def preprocess_md(md: str, snippet_len: int = 200) -> Tuple[str, str, str]:
    title, body = split_title_body(fulltext=md)
    title = md2txt(title.strip())
    body = md2txt(body.strip())
    snippet = strip_html_tags(body)[:snippet_len]
    return title, body, snippet


def md2html(md: str, with_css=False) -> str:
    _html = __md_html.convert(md)
    # prevent XSS and other security issues
    _html = re.sub(r"<script[^>]*>.*?</script>", "", _html, flags=re.DOTALL)
    if not with_css:
        return _html
    return __markdown_html_template.format(css=__css, html=_html)


def get_at_node_md_link(title: str, nid: str) -> str:
    return f"[@{title}](/n/{nid})"


def change_link_title(md: str, nid: str, new_title: str) -> str:
    new_md = re.sub(
        r"\[@[^].]*?]\(/n/{}/?\)".format(nid),
        get_at_node_md_link(new_title, nid),
        md,
    )
    return new_md


def split_title_body(fulltext: str) -> (str, str):
    title_body = fulltext.split("\n", maxsplit=1)
    title = title_body[0].strip()
    try:
        body = title_body[1].strip()
    except IndexError:
        body = ""
    return title, body


def contain_only_http_link(md: str) -> str:
    content = md.strip()
    if regex.ONLY_HTTP_URL.match(content) is None:
        return ""
    return content
