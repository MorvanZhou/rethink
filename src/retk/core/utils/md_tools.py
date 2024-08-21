import os
import re
import zipfile
from io import BytesIO
from typing import Tuple, Set, AsyncIterable, Literal

from retk import const, config
from retk.core.utils.cos import cos_client
from retk.utils import md2html


def replace_app_files_in_md(uid: str, md: str) -> Tuple[str, Set[str]]:
    # return new_md and file_links
    if config.is_local_db():
        filenames = re.findall(rf"\[.*]\(/{const.settings.LOCAL_FILE_URL_PRE_DIR}/(.*)\)", md)
        new_md = md
    else:
        url = f"https://{cos_client.domain}/{cos_client.get_user_data_key(uid, '')}"
        filenames = re.findall(rf"\[.*]\({url}(.*)\)", md)
        new_md = re.sub(
            rf"(\[.*]\(){url}(.*)\)",
            rf"\1{const.settings.LOCAL_FILE_URL_PRE_DIR}/\2)",
            md,
        )
    return new_md, set(filenames)


async def iter_remote_files(uid: str, filenames: Set[str]) -> AsyncIterable[Tuple[str, bytes]]:
    settings = config.get_settings()
    if config.is_local_db():
        data_dir = os.path.join(
            settings.RETHINK_LOCAL_STORAGE_PATH,
            const.settings.DOT_DATA, const.settings.LOCAL_FILE_URL_PRE_DIR
        )
        for filename in filenames:
            path = os.path.join(data_dir, filename)
            try:
                with open(path, "rb") as file:
                    b = file.read()
            except FileNotFoundError:
                continue
            yield filename, b
    else:
        files = await cos_client.async_batch_get(uid=uid, filenames=filenames)
        for filename, b in files.items():
            yield filename, b


async def md_export(
        uid: str,
        title: str,
        md: str,
        format_: Literal["md", "html", "pdf"],
) -> Tuple[str, BytesIO]:
    buffer = BytesIO()
    content, filenames = replace_app_files_in_md(uid, md)
    if format_ == "md":
        out_filename = f"{title}.md"
        media_type = "text/markdown"
    elif format_ == "html":
        content = md2html(content, with_css=True)
        out_filename = f"{title}.html"
        media_type = "text/html"
    # elif format_ == "pdf":
    #     out_filename = f"{title}.pdf"
    #     media_type = "application/pdf"
    else:
        raise ValueError(f"unknown format: {format_}")

    if len(filenames) > 0:
        with zipfile.ZipFile(buffer, "w") as z:
            async for name, file in iter_remote_files(uid, filenames):
                z.writestr(f"/{const.settings.LOCAL_FILE_URL_PRE_DIR}/{name}", file)
            z.writestr(out_filename, content)
        media_type = "application/zip"
    else:
        # only contain a single md file
        buffer.write(content.encode("utf-8"))

    buffer.seek(0)
    return media_type, buffer
