import io
import zipfile
from platform import system
from typing import Dict, Union


def unzip_file(zip_bytes: bytes) -> Dict[str, Dict[str, Union[bytes, int]]]:
    with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as ref:
        filepaths = ref.namelist()
        extracted_files = {}
        for filepath in filepaths:
            info = ref.getinfo(filepath)
            try:
                if system() in ["Darwin", "Linux"]:
                    _filepath = filepath.encode('cp437').decode('utf-8')
                elif system() == "Windows":
                    _filepath = filepath.encode('cp437').decode('gbk')
                else:
                    _filepath = filepath
            except UnicodeEncodeError:
                if system() == "Windows":
                    _filepath = filepath.encode("utf-8").decode("utf-8")
                _filepath = filepath
            sp = _filepath.split("/")
            if sp[0] in ["__MACOSX", ".DS_Store"]:
                continue
            if len(sp) > 1:
                _filepath = "/".join(sp[1:])
            if _filepath.strip() == "" or _filepath.startswith("."):
                continue
            extracted_files[_filepath] = {
                "file": ref.read(filepath),
                "size": info.file_size,
            }

    return extracted_files
