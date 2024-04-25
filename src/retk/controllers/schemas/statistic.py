from pydantic import Field, BaseModel

from retk.const import settings, USER_BEHAVIOR_TYPE_MAP

_max_len_behavior_type = len(USER_BEHAVIOR_TYPE_MAP)


class UserBehaviorRequest(BaseModel):
    type: int = Field(le=_max_len_behavior_type)
    remark: str = Field(default="", max_length=settings.MAX_STATISTIC_REMARK_LENGTH)
