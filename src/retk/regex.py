import re

from retk import const

# at least 6 characters, at most 20 characters, at least one letter and one number
VALID_PASSWORD = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{6,20}$")

EMAIL = re.compile(r'^[.0-9a-zA-Z_]{1,18}@([0-9a-zA-Z-]{1,13}\.){1,}[a-zA-Z]{1,3}$')

MD_CODE = re.compile(r"^```[^\S\r\n]*[a-z]*?\n(.*?)\n```$", re.MULTILINE | re.DOTALL)

OBS_INTERNAL_LINK = re.compile(r"\[\[(.*?)]]")
OBS_INTERNAL_FILE = re.compile(r"!\[\[(.*?)]]")
MD_IMG = re.compile(r"!\[(.*?)]\((?!http)(.*?)\)")

MD_AT_LINK = re.compile(r"\[@.+?]\(([\w/]+?)\)", re.MULTILINE)
NID = re.compile(fr"^[A-Za-z0-9]{{20,{const.settings.NID_MAX_LENGTH}}}$")

ONLY_HTTP_URL = re.compile(r"^https?://\S*$")

MD_FILE_EXT = re.compile(r"^(.+)\.md$")
