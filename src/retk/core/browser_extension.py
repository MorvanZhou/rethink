from typing import List, Tuple, Optional

from fastapi import UploadFile

from retk import const
from retk.core import node, user
from retk.core.files.importing import sync_tasks
from retk.core.files.upload import fetch_image_vditor
from retk.models.tps import AuthedUser, Node


async def post_node(
        au: AuthedUser,
        url: str,
        title: str,
        content: str,
        referer: str,
        user_agent: str,
        images: List[UploadFile],
) -> Tuple[Optional[Node], const.CodeEnum]:
    if len(images):
        if await user.user_space_not_enough(au=au):
            return None, const.CodeEnum.USER_SPACE_NOT_ENOUGH

    filtered_images = []
    for file in images:
        if file.size == 0:
            new_url, code = await fetch_image_vditor(au=au, url=file.filename, referer=referer, user_agent=user_agent)
            if code == const.CodeEnum.OK:
                content = content.replace(file.filename, new_url)
            continue
        if not file.content_type.startswith(const.app.ValidUploadedFilePrefixEnum.IMAGE.value):
            continue
        filtered_images.append(file)
    res = await sync_tasks.save_editor_upload_files(
        uid=au.u.id,
        files=filtered_images,
    )

    for original_url, new_url in res["succMap"].items():
        content = content.replace(original_url, new_url)
    if au.language == const.LanguageEnum.ZH.value:
        source_postfix = "原文来自:"
    elif au.language == const.LanguageEnum.EN.value:
        source_postfix = "Source from:"
    else:
        source_postfix = "Source from:"
    md = f"{title}\n\n{content}\n\n{source_postfix} [{url}]({url})"
    n, code = await node.post(
        au=au,
        md=md,
        type_=const.NodeTypeEnum.MARKDOWN.value,
        from_nid="",
    )
    return n, code
