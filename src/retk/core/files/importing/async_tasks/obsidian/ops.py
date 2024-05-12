import io
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from os.path import normpath
from pathlib import Path
from typing import Tuple, Dict, Optional

from retk import regex, const
from retk.core.files.saver import saver, File
from retk.utils import short_uuid


@dataclass
class UnzipObsidian:
    @dataclass
    class Meta:
        __slots__ = ["filepath", "filename", "title", "file", "size", "duplicate", "created_at"]
        filepath: str
        filename: str
        title: str
        file: bytes
        size: int
        duplicate: bool
        created_at: Optional[datetime]

    md: Dict[str, Meta] = field(default_factory=dict)
    md_full: Dict[str, Meta] = field(default_factory=dict)
    others: Dict[str, Meta] = field(default_factory=dict)
    others_full: Dict[str, Meta] = field(default_factory=dict)


async def __file_ptn_replace_upload(
        uid: str,
        filepath: str,
        filename: str,  # with ext
        md: str,
        others_full: Dict[str, UnzipObsidian.Meta],
        others_name: Dict[str, UnzipObsidian.Meta],
        span: Tuple[int, int]
) -> str:
    """

    Args:
        filepath:
        filename:
        md:
        others_full:
        others_name:
        span:

    Returns:
        md, uploaded_file_size
    """
    try:
        meta = others_name[filename]
    except KeyError:
        try:
            meta = others_full[filepath]
        except KeyError:
            # not inner file
            return md
    file = File(
        filename=meta.filename,
        data=io.BytesIO(meta.file),
    )
    # file type not recognized
    if file.is_unknown_type():
        return md

    url = await saver.save(
        uid=uid,
        file=file
    )

    if url != "":
        img_ptn = "!" if file.type == const.app.FileTypesEnum.IMAGE else ""
        md = f"{md[: span[0]]}{img_ptn}[{filename}]({url}){md[span[1]:]}"
    return md


async def replace_inner_link_and_upload(
        uid: str,
        md: str,
        exist_path2nid: Dict[str, str],
        others_full: Dict[str, UnzipObsidian.Meta],
        others_name: Dict[str, UnzipObsidian.Meta],
) -> str:
    """

    Args:
        uid:
        md:
        exist_path2nid:
        others_full:
        others_name:

    Returns:
        md
    """
    # orig image link to inner image file
    for match in list(regex.MD_IMG.finditer(md))[::-1]:
        span = match.span()
        filename = match.group(1)
        filepath = match.group(2)

        # ![xxx](aa/bb/cc.png)
        md = await __file_ptn_replace_upload(
            uid=uid,
            filepath=filepath,  # full path in zip
            filename=filename,  # filename in md
            md=md,
            others_full=others_full,
            others_name=others_name,
            span=span,
        )

    # files
    for match in list(regex.OBS_INTERNAL_FILE.finditer(md))[::-1]:
        span = match.span()
        filepath = match.group(1)

        # ![[aa/bb/cc.png]]
        # ![[aa.pdf]]
        md = await __file_ptn_replace_upload(
            uid=uid,
            filepath=filepath,
            filename=Path(filepath).name,
            md=md,
            others_full=others_full,
            others_name=others_name,
            span=span,
        )

    # node link
    for match in list(regex.OBS_INTERNAL_LINK.finditer(md))[::-1]:
        span = match.span()
        filename = match.group(1)
        path = f"{filename}.md"
        try:
            nid = exist_path2nid[path]
        except KeyError:
            nid = short_uuid()
            exist_path2nid[path] = nid
        md = f"{md[: span[0]]}[@{filename}](/n/{nid}){md[span[1]:]}"
    return md


def _decode_filename(filepath: str) -> str:
    encodings = ['utf-8', 'gbk', 'cp437']
    for encoding in encodings:
        try:
            return filepath.encode('cp437').decode(encoding)
        except (UnicodeDecodeError, UnicodeEncodeError):
            continue
    return filepath


def unzip_obsidian(zip_bytes: bytes) -> UnzipObsidian:  # noqa: C901
    with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
        filepaths = zf.namelist()
        extracted_files = UnzipObsidian()
        for filepath in filepaths:
            info = zf.getinfo(filepath)
            if info.is_dir():
                continue
            try:
                _filepath = _decode_filename(filepath)
            except UnicodeDecodeError:
                _filepath = filepath
            fp = Path(_filepath.split("/", 1)[-1])
            # filter out system files
            has_invalid_suffix = False
            for p in fp.parts:
                if p.startswith(".") or fp.name.startswith("__MACOSX"):
                    has_invalid_suffix = True
                    break
            if has_invalid_suffix:
                continue

            # Check for directory traversal
            norm_path = normpath(fp)
            if norm_path.startswith('../') or norm_path.startswith('..\\'):
                continue  # or raise an exception
            try:
                title = regex.MD_FILE_EXT.findall(fp.name)[0]
            except IndexError:
                title = fp.name

            meta = UnzipObsidian.Meta(
                filepath=norm_path,
                filename=fp.name,
                title=title,
                file=zf.read(filepath),
                size=info.file_size,
                duplicate=False,
                created_at=datetime(*info.date_time),
            )

            if fp.suffix.lower() == ".md":
                entry = extracted_files.md
                entry_full = extracted_files.md_full
            else:
                entry = extracted_files.others
                entry_full = extracted_files.others_full

            if fp.name in entry:
                meta.duplicate = True
            else:
                entry[fp.name] = meta
            entry_full[str(fp)] = meta

    return extracted_files
