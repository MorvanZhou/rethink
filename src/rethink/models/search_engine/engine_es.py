import datetime
from typing import List, Tuple, Sequence

from bson.tz_util import utc
from elasticsearch import AsyncElasticsearch
from elasticsearch import helpers

from rethink import const
from rethink.config import get_settings
from rethink.logger import logger
from rethink.models.search_engine.engine import BaseEngine, SearchDoc, SearchResult, RestoreSearchDoc


def datetime2str(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def get_utc_now() -> str:
    now = datetime.datetime.now(tz=utc)
    return datetime2str(now)


class ESSearcher(BaseEngine):
    es: AsyncElasticsearch
    properties = {
        "uid": {
            "type": "keyword"
        },
        "title": {
            "type": "text",
            "analyzer": "ik_analyzer",
            "search_analyzer": "ik_smart",
            "fields": {
                "keyword": {
                    "type": "keyword"
                }
            }
        },
        "disabled": {
            "type": "boolean"
        },
        "inTrash": {
            "type": "boolean"
        },
        "body": {
            "type": "text",
            "analyzer": "ik_analyzer",
            "search_analyzer": "ik_smart"
        },
        "modifiedAt": {
            "type": "date",
            "format": "strict_date_optional_time_nanos",
        },
        "createdAt": {
            "type": "date",
            "format": "strict_date_optional_time_nanos",
        }
    }
    analysis = {
        "analyzer": {
            "ik_analyzer": {
                "type": "custom",
                "tokenizer": "ik_max_word",
                "filter": [
                    "lowercase",
                    "english_stop"
                ]
            },
            "en_analyzer": {
                "type": "custom",
                "tokenizer": "standard",
                "filter": [
                    "lowercase",
                    "english_stop"
                ]
            }
        },
        "filter": {
            "english_stop": {
                "type": "stop",
                "stopwords": "_english_"
            }
        }
    }

    def connect(self):
        try:
            self.es
        except AttributeError:
            self.es = AsyncElasticsearch(
                hosts=get_settings().ES_HOSTS.split(","),
                # sniff_on_start=True,
                # sniff_on_node_failure=True,
                # min_delay_between_sniffing=60,
                basic_auth=(get_settings().ES_USER, get_settings().ES_PASSWORD),
                request_timeout=5,
            )

    async def init(self):
        # please install es 8.11.0
        self.connect()
        info = await self.es.info()
        if info.body["version"]["number"] != "8.11.0":
            raise ValueError("please install es 8.11.0")

        if not await self.es.indices.exists(index=get_settings().ES_INDEX):
            # install ik plugin: https://github.com/medcl/elasticsearch-analysis-ik
            resp = await self.es.indices.create(
                index=get_settings().ES_INDEX,
                body={
                    "settings": {
                        "index": {
                            "number_of_shards": 1,
                            "number_of_replicas": 0,
                            "refresh_interval": "2s",
                        },
                        "analysis": self.analysis,
                    },
                    "mappings": {
                        "properties": self.properties,
                    }
                }
            )
            if resp.meta.status != 200:
                raise RuntimeError(f"create index failed, resp: {resp}")

    async def drop(self):
        self.connect()
        if await self.es.indices.exists(index=get_settings().ES_INDEX):
            await self.es.indices.delete(index=get_settings().ES_INDEX)
        await self.es.close()
        del self.es

    async def add(self, uid: str, doc: SearchDoc) -> const.Code:
        now = get_utc_now()
        resp = await self.es.index(
            index=get_settings().ES_INDEX,
            document={
                "uid": uid,
                "title": doc.title,
                "body": doc.body,
                "modifiedAt": now,
                "createdAt": now,
                "disabled": False,
                "inTrash": False,
            },
            id=doc.nid,
        )
        if resp.meta.status != 201:
            logger.error(f"add failed {uid=} {doc.nid=}")
            return const.Code.OPERATION_FAILED
        return const.Code.OK

    async def update(self, uid: str, doc: SearchDoc) -> const.Code:
        now = get_utc_now()
        resp = await self.es.update(
            index=get_settings().ES_INDEX,
            id=doc.nid,
            body={
                "doc": {
                    "uid": uid,
                    "title": doc.title,
                    "body": doc.body,
                    "modifiedAt": now,
                }
            }
        )
        if resp.meta.status != 200:
            logger.error(f"update failed {uid=} {doc.nid=}")
            return const.Code.OPERATION_FAILED
        return const.Code.OK

    async def to_trash(self, uid: str, nid: str) -> const.Code:
        resp = await self.es.update(
            index=get_settings().ES_INDEX,
            id=nid,
            body={
                "doc": {
                    "inTrash": True,
                }
            }
        )
        if resp.meta.status != 200:
            logger.error(f"to trash failed {uid=} {nid=}")
            return const.Code.OPERATION_FAILED
        return const.Code.OK

    async def batch_to_trash(self, uid: str, nids: List[str]) -> const.Code:
        resp = await helpers.async_bulk(
            client=self.es,
            actions=[
                {
                    "_op_type": "update",
                    "_index": get_settings().ES_INDEX,
                    "_id": nid,
                    "doc": {
                        "inTrash": True,
                    }
                }
                for nid in nids
            ]
        )
        if resp[0] != len(nids):
            logger.error(f"to trash batch failed, resp: {resp}")
            return const.Code.OPERATION_FAILED
        return const.Code.OK

    async def restore_from_trash(self, uid: str, nid: str) -> const.Code:
        resp = await self.es.update(
            index=get_settings().ES_INDEX,
            id=nid,
            body={
                "doc": {
                    "inTrash": False,
                }
            }
        )
        if resp.meta.status != 200:
            logger.error(f"restore from trash failed {uid=} {nid=}")
            return const.Code.OPERATION_FAILED
        return const.Code.OK

    async def restore_batch_from_trash(self, uid: str, nids: str) -> const.Code:
        resp = await helpers.async_bulk(
            client=self.es,
            actions=[
                {
                    "_op_type": "update",
                    "_index": get_settings().ES_INDEX,
                    "_id": nid,
                    "doc": {
                        "inTrash": False,
                    }
                }
                for nid in nids
            ]
        )
        if resp[0] != len(nids):
            logger.error(f"restore batch from trash failed, resp: {resp}")
            return const.Code.OPERATION_FAILED
        return const.Code.OK

    async def disable(self, uid: str, nid: str) -> const.Code:
        resp = await self.es.update(
            index=get_settings().ES_INDEX,
            id=nid,
            body={
                "doc": {
                    "disabled": True,
                }
            }
        )
        if resp.meta.status != 200:
            logger.error(f"disable failed {uid=} {nid=}")
            return const.Code.OPERATION_FAILED
        return const.Code.OK

    async def enable(self, uid: str, nid: str) -> const.Code:
        resp = await self.es.update(
            index=get_settings().ES_INDEX,
            id=nid,
            body={
                "doc": {
                    "disabled": False,
                }
            }
        )
        if resp.meta.status != 200:
            logger.error(f"enable failed {uid=} {nid=}")
            return const.Code.OPERATION_FAILED
        return const.Code.OK

    async def delete(self, uid: str, nid: str) -> const.Code:
        doc = await self.es.get(
            index=get_settings().ES_INDEX,
            id=nid,
        )
        if doc["_source"]["uid"] != uid:
            logger.error(f"node not belong to user {uid=} {nid=}")
            return const.Code.NODE_NOT_EXIST
        if not doc["_source"]["inTrash"]:
            logger.error(f"doc not in trash, deletion failed {uid=} {nid=}")
            return const.Code.OPERATION_FAILED

        resp = await self.es.delete(
            index=get_settings().ES_INDEX,
            id=nid,
        )
        if resp.meta.status != 201:
            logger.error(f"delete failed {uid=} {nid=}")
            return const.Code.OPERATION_FAILED
        return const.Code.OK

    async def add_batch(self, uid: str, docs: List[SearchDoc]) -> const.Code:
        actions = []
        now = datetime.datetime.now(tz=utc)
        for doc in docs:
            d = doc.__dict__
            d["inTrash"] = False
            d["disabled"] = False
            d["createdAt"] = datetime2str(now)
            d["modifiedAt"] = d["createdAt"]
            d["uid"] = uid
            nid = d.pop("nid")
            # insert a creation operation
            actions.append({
                "_op_type": "create",
                "_index": get_settings().ES_INDEX,
                "_id": nid,
                "_source": d
            })
            now = now + datetime.timedelta(seconds=0.001)
        return await self._batch_ops(actions, op_type="add")

    async def delete_batch(self, uid: str, nids: List[str]) -> const.Code:
        resp = await self.es.delete_by_query(
            index=get_settings().ES_INDEX,
            body={
                "query": {
                    "bool": {
                        "must": [
                            {"ids": {"values": nids}},
                            {
                                "term": {
                                    "uid": uid
                                }
                            },
                            {
                                "term": {
                                    "inTrash": True
                                }
                            }
                        ]
                    }
                }
            }
        )

        if resp.meta.status != 200:
            logger.error(f"delete batch failed, resp: {resp}")
            return const.Code.OPERATION_FAILED
        if resp.body["deleted"] != len(nids):
            logger.error(f"delete batch failed, resp: {resp}")
            return const.Code.OPERATION_FAILED
        return const.Code.OK

    async def update_batch(self, uid: str, docs: List[SearchDoc]) -> const.Code:
        actions = []
        now = datetime.datetime.now(tz=utc)
        for doc in docs:
            d = doc.__dict__
            d["modifiedAt"] = datetime2str(now)
            d["uid"] = uid
            nid = d.pop("nid")
            actions.append({
                "_op_type": "update",
                "_index": get_settings().ES_INDEX,
                "_id": nid,
                "doc": d
            })
            now = now + datetime.timedelta(seconds=0.001)
        return await self._batch_ops(actions, op_type="update")

    async def search(
            self,
            uid: str,
            query: str = "",
            sort_key: str = None,
            reverse: bool = False,
            page: int = 0,
            page_size: int = 10,
            exclude_nids: Sequence[str] = None,
    ) -> Tuple[List[SearchResult], int]:
        if page < 0:
            raise ValueError("page must >= 0")
        if sort_key is None or sort_key in ["", "similarity"]:
            sort = ["_score"]
        elif sort_key == "title":
            sort = [{"title.keyword": {"order": "desc" if reverse else "asc"}}, "_score"]
        elif sort_key in ["createdAt", "modifiedAt"]:
            sort = [
                {sort_key: {
                    "order": "desc" if reverse else "asc",
                    "format": "strict_date_optional_time_nanos"
                }},
                "_score",
            ]
        else:
            raise ValueError(f"sort_key {sort_key} not supported")
        # select uid = uid, disabled = false, inTrash = false
        query_dict = {
            "bool": {
                "must": [
                    {
                        "term": {
                            "uid": uid
                        }
                    },
                    {
                        "term": {
                            "disabled": False
                        }
                    },
                    {
                        "term": {
                            "inTrash": False
                        }
                    }
                ]
            }
        }
        if query != "":
            q_lower = query.lower()
            # search q_lower on both title and body
            query_dict["bool"]["must"].append({
                "bool": {
                    "should": [
                        {
                            "match": {
                                "title": {
                                    "query": q_lower,
                                    "boost": 2,
                                }
                            }
                        },
                        {
                            "match": {
                                "body": {
                                    "query": q_lower,
                                    "boost": 1,
                                }
                            }
                        }
                    ]
                }
            })
        if exclude_nids is not None and len(exclude_nids) > 0:
            query_dict["bool"]["must_not"] = [{
                "ids": {
                    "values": exclude_nids
                }
            }]

        resp = await self.es.search(
            index=get_settings().ES_INDEX,
            body={
                "query": query_dict,
                "sort": sort,
                "from": page * page_size,
                "size": page_size,
                "highlight": {
                    "pre_tags": [
                        f"<{self.hl_tag_name} class=\"{self.hl_class_name} {self.hl_term_prefix}{i}\">"
                        for i in range(5)
                    ],
                    "post_tags": [f"</{self.hl_tag_name}>" for _ in range(5)],
                    "fields": {
                        "body": {},
                        "title": {},
                    }
                },
            })
        hits = resp["hits"]["hits"]
        total = resp["hits"]["total"]["value"]
        return [
            SearchResult(
                nid=hit["_id"],
                score=hit["_score"] if hit["_score"] is not None else 0.,
                titleHighlight=self.get_hl(hit, "title", first=True, default=hit["_source"]["title"]),
                bodyHighlights=self.get_hl(hit, "body", first=False, default=hit["_source"]["body"][:60] + "..."),
            ) for hit in hits
        ], total

    async def count_all(self) -> int:
        resp = await self.es.count(
            index=get_settings().ES_INDEX,
            body={
                "query": {
                    "match_all": {}
                }
            })
        return resp["count"]

    async def refresh(self):
        await self.es.indices.refresh(index=get_settings().ES_INDEX)

    async def batch_restore_docs(self, uid: str, docs: List[RestoreSearchDoc]) -> const.Code:
        actions = []
        for doc in docs:
            d = doc.__dict__
            d["createdAt"] = datetime2str(d["createdAt"])
            d["modifiedAt"] = datetime2str(d["modifiedAt"])
            d["uid"] = uid
            nid = d.pop("nid")
            # insert a creation operation
            actions.append({
                "_op_type": "create",
                "_index": get_settings().ES_INDEX,
                "_id": nid,
                "_source": d
            })
        return await self._batch_ops(actions, "restore")

    async def _batch_ops(self, actions: List[dict], op_type: str) -> const.Code:
        try:
            resp = await helpers.async_bulk(client=self.es, actions=actions)
        except helpers.BulkIndexError as e:
            logger.error(f"{op_type} batch failed, resp: {e.args[0]}")
            return const.Code.OPERATION_FAILED
        if resp[0] != len(actions):
            logger.error(f"{op_type} batch failed, resp: {resp}")
            return const.Code.OPERATION_FAILED
        return const.Code.OK

    @staticmethod
    def get_hl(hit: dict, key: str, first: bool, default: str = ""):
        if "highlight" not in hit:
            if first:
                return default
            return []
        if key not in hit["highlight"]:
            if first:
                return default
            return [default]
        if first:
            if len(hit["highlight"][key]) > 0:
                return hit["highlight"][key][0]
            return default
        return hit["highlight"][key]
