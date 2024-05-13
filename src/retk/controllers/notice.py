from retk.controllers import schemas, utils
from retk.core import notice
from retk.models.tps import AuthedUser


async def post_in_manager_delivery(
        au: AuthedUser,
        req: schemas.notice.ManagerNoticeDeliveryRequest,
) -> schemas.RequestIdResponse:
    _, code = await notice.post_in_manager_delivery(
        au=au,
        title=req.title,
        content=req.content,
        recipient_type=req.recipientType,
        batch_type_ids=req.batchTypeIds,
        publish_at=req.publishAt,
    )
    utils.maybe_raise_json_exception(au=au, code=code)

    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )


async def get_user_notice(
        au: AuthedUser,
) -> schemas.notice.NotificationResponse:
    nt, code = await notice.get_user_notice(au=au)
    utils.maybe_raise_json_exception(au=au, code=code)

    return schemas.notice.NotificationResponse(
        requestId=au.request_id,
        data=schemas.notice.NotificationResponse.Data(
            system=[
                schemas.notice.NotificationResponse.Data.System(
                    id=str(n["_id"]),
                    title=n["title"],
                    content=n["content"],
                    publishAt=n["publishAt"],
                    read=n["read"],
                    readTime=n["readTime"],
                ) for n in nt["system"]],
        ),
    )
