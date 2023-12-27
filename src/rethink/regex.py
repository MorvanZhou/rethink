import re

# at least 6 characters, at most 20 characters, at least one letter and one number
VALID_PASSWORD_PTN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{6,20}$")

EMAIL_PTN = re.compile(r'^[.0-9a-zA-Z_]{1,18}@([0-9a-zA-Z-]{1,13}\.){1,}[a-zA-Z]{1,3}$')
