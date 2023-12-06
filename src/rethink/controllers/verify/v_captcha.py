from fastapi.responses import StreamingResponse

from rethink.models.verify.verification import random_captcha


def get_captcha_img():
    token, data = random_captcha(length=4, sound=False)
    return StreamingResponse(
        data["img"],
        headers={
            "X-Captcha-Token": token
        },
        media_type="image/png",
    )
