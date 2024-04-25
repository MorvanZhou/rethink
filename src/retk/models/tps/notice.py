from typing import TypedDict

from bson import ObjectId


class SystemNotice(TypedDict):
    _id: ObjectId
    senderType: int  # user type, only admin and manager can send
    senderId: str
    title: str
    content: str
    receiverGroup: int  # send to which user type, 0: all, 1: batch, 2: admin, 3: manager
    scheduled: bool  # has been scheduled to sent to user


class UserNotice(TypedDict):
    _id: ObjectId
    uid: str
    noticeType: int
    noticeId: str
    read: bool
    readTime: int
