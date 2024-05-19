from datetime import datetime
from typing import TypedDict, List

from bson import ObjectId


# system notice from sender
class NoticeManagerDelivery(TypedDict):
    _id: ObjectId
    senderType: int  # user type, only admin and manager can send
    senderId: str
    title: str
    html: str
    snippet: str
    recipientType: int  # send to which user type, 0: batch, 1: all, 2: admin, 3: manager
    batchTypeIds: List[str]  # if recipient=batch, put user id here
    publishAt: datetime  # publish time
    scheduled: bool  # has been scheduled to sent to user


# system notice receiver
class NoticeSystem(TypedDict):
    _id: ObjectId
    senderId: str  # sender's uid
    recipientId: str  # recipient's uid
    noticeId: ObjectId  # notice _id
    read: bool  # has been read
    readTime: datetime  # read time

# event notice
# class EventRemind(TypedDict):
#     _id: ObjectId
#     event: int     # action type, 0: user reply, 1: user like, 2: user at, 3: user subscribe, 4: subscribe new post
#     senderId: str   # sender's uid
#     title: str
#     content: str
#     recipientId: str    # recipient's uid
#     read: bool      # has been read
#     readTime: datetime   # read time
