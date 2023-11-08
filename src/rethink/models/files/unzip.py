import io
import zipfile
from platform import system
from typing import Dict


def unzip_file(zip_bytes: bytes) -> Dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as ref:
        filepaths = ref.namelist()
        extracted_files = {}
        for filepath in filepaths:
            try:
                if system() in ["Darwin", "Linux"]:
                    _filepath = filepath.encode('cp437').decode('utf-8')
                elif system() == "Windows":
                    _filepath = filepath.encode('utf-8').decode('utf-8')
                else:
                    _filepath = filepath
            except UnicodeEncodeError:
                _filepath = filepath
            sp = _filepath.split("/")
            if sp[0] in ["__MACOSX", ".DS_Store"]:
                continue
            if len(sp) > 1:
                _filepath = "/".join(sp[1:])
            if _filepath.strip() == "" or _filepath.startswith("."):
                continue
            extracted_files[_filepath] = ref.read(filepath)

    return extracted_files
