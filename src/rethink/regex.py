import re

from rethink import const

# at least 6 characters, at most 20 characters, at least one letter and one number
VALID_PASSWORD = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{6,20}$")

EMAIL = re.compile(r'^[.0-9a-zA-Z_]{1,18}@([0-9a-zA-Z-]{1,13}\.){1,}[a-zA-Z]{1,3}$')

MD_CODE = re.compile(r"^```[^\S\r\n]*[a-z]*?\n(.*?)\n```$", re.MULTILINE | re.DOTALL)

OBS_INTERNAL_LINK = re.compile(r"\[\[(.*?)]]")
OBS_INTERNAL_IMG = re.compile(r"!\[\[(Pasted image .*?)]]")
MD_IMG = re.compile(r"!\[(.*?)]\((?!http)(.*?)\)")

MD_AT_LINK = re.compile(r"\[@[ \w\u4e00-\u9fa5！？。，￥【】「」]+?]\(([\w/]+?)\)", re.MULTILINE)
NID = re.compile(fr"^[A-Za-z0-9]{{20,{const.NID_MAX_LENGTH}}}$")

ONLY_HTTP_URL = re.compile(r"^https?://\S*$")
