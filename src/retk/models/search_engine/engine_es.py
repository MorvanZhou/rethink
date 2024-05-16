import datetime
from typing import List, Tuple, Sequence, Dict, Any, Literal

from bson.tz_util import utc
from elastic_transport import ObjectApiResponse
from elasticsearch import AsyncElasticsearch, helpers

from retk import const
from retk.config import get_settings
from retk.logger import logger
from retk.models.search_engine.engine import (
    BaseEngine, SearchDoc, SearchResult, RestoreSearchDoc, STOPWORDS,
)
from retk.models.tps import AuthedUser


def datetime2str(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def get_utc_now() -> str:
    now = datetime.datetime.now(tz=utc)
    return datetime2str(now)


class ESSearcher(BaseEngine):
    es: AsyncElasticsearch
    index: str
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
                    "english_stop",
                ]
            },
            "search_stop_analyzer": {
                "type": "custom",
                "char_filter": [],
                "tokenizer": "ik_smart",
                "filter": [
                    "lowercase",
                    "english_stop",
                    "cn_stop",
                ]
            },
            "en_analyzer": {
                "type": "custom",
                "tokenizer": "standard",
                "filter": [
                    "lowercase",
                    "english_stop"
                ]
            },

        },
        "filter": {
            "english_stop": {
                "type": "stop",
                "stopwords": "_english_",
            },
            "cn_stop": {
                "type": "stop",
                "stopwords": STOPWORDS,
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.index = ""

    async def connect(self):
        try:
            self.es
        except AttributeError:
            # config the elastic.yml file, disable ssl for local usage, add a user and password
            self.es = AsyncElasticsearch(
                hosts=get_settings().ES_HOSTS.split(","),
                # sniff_on_start=True,
                # sniff_on_node_failure=True,
                # min_delay_between_sniffing=60,
                basic_auth=(get_settings().ES_USER, get_settings().ES_PASSWORD),
                request_timeout=5,
            )
            resp = await self.es.indices.get_alias(index=f"{get_settings().ES_INDEX_ALIAS}-*")
            for index, aliases in resp.body.items():
                if get_settings().ES_INDEX_ALIAS in aliases["aliases"]:
                    self.index = index
                    break

    async def init(self):
        # please install es 8.11.0
        await self.connect()
        info = await self.es.info()
        if info.body["version"]["number"] != "8.11.0":
            raise ValueError("please install es 8.11.0")

        # if no index found, create one
        if self.index == "" or not await self.es.indices.exists(index=self.index):
            # install ik plugin: https://github.com/medcl/elasticsearch-analysis-ik
            self.index = f"{get_settings().ES_INDEX_ALIAS}-1"
            resp = await self.es.indices.create(
                index=self.index,
                aliases={get_settings().ES_INDEX_ALIAS: {}},
                settings={
                    "index": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                        "refresh_interval": "3s",
                    },
                    "analysis": self.analysis,
                },
                mappings={
                    "properties": self.properties,
                }
            )
            if resp.meta.status != 200:
                raise RuntimeError(f"create index failed, resp: {resp}")

        settings = await self.es.indices.get_settings(index=self.index)
        try:
            analysis = settings.body[self.index]["settings"]["index"]["analysis"]
            if analysis != self.analysis:
                await self.reindex()
        except KeyError:
            await self.reindex()

    async def reindex(self):
        await self.connect()
        new_index_num = int(self.index.split("-")[-1]) + 1
        new_index = f"{get_settings().ES_INDEX_ALIAS}-{new_index_num}"

        resp = await self.es.indices.create(
            index=new_index,
            aliases={get_settings().ES_INDEX_ALIAS: {}},
            settings={
                "index": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "refresh_interval": "3s",
                },
                "analysis": self.analysis,
            },
            mappings={
                "properties": self.properties,
            }
        )
        if resp.meta.status != 200:
            raise RuntimeError(f"create index for reindexing failed, resp: {resp}")

        resp = await self.es.reindex(
            body={
                "source": {
                    "index": self.index,
                },
                "dest": {
                    "index": new_index,
                }
            }
        )
        if resp.meta.status != 200:
            raise RuntimeError(f"reindex failed, resp: {resp}")
        resp = await self.es.indices.delete(index=self.index)
        if resp.meta.status != 200:
            raise RuntimeError(f"reindex failed, resp: {resp}")

        self.index = new_index
        logger.debug(f"elasticsearch reindex finished, new index: {self.index}")

    async def close(self):
        await self.es.close()

    async def drop(self):
        await self.connect()
        if self.index != "" and await self.es.indices.exists(index=self.index):
            await self.es.indices.delete(index=self.index)
        self.index = ""
        await self.es.close()
        del self.es

    async def add(self, au: AuthedUser, doc: SearchDoc) -> const.CodeEnum:
        now = get_utc_now()
        resp = await self.es.index(
            index=self.index,
            document={
                "uid": au.u.id,
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
            logger.error(f"add failed {au.u.id=} {doc.nid=}")
            return const.CodeEnum.OPERATION_FAILED
        return const.CodeEnum.OK

    async def update(self, au: AuthedUser, doc: SearchDoc) -> const.CodeEnum:
        now = get_utc_now()
        resp = await self.es.update(
            index=self.index,
            id=doc.nid,
            body={
                "doc": {
                    "uid": au.u.id,
                    "title": doc.title,
                    "body": doc.body,
                    "modifiedAt": now,
                }
            }
        )
        if resp.meta.status != 200:
            logger.error(f"update failed {au.u.id=} {doc.nid=}")
            return const.CodeEnum.OPERATION_FAILED
        return const.CodeEnum.OK

    async def to_trash(self, au: AuthedUser, nid: str) -> const.CodeEnum:
        resp = await self.es.update(
            index=self.index,
            id=nid,
            body={
                "doc": {
                    "inTrash": True,
                }
            },
            refresh=True,
        )
        if resp.meta.status != 200:
            logger.error(f"to trash failed {au.u.id=} {nid=}")
            return const.CodeEnum.OPERATION_FAILED
        return const.CodeEnum.OK

    async def batch_to_trash(self, au: AuthedUser, nids: List[str]) -> const.CodeEnum:
        resp = await helpers.async_bulk(
            client=self.es,
            actions=[
                {
                    "_op_type": "update",
                    "_index": get_settings().ES_INDEX_ALIAS,
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
            return const.CodeEnum.OPERATION_FAILED
        await self.refresh()
        return const.CodeEnum.OK

    async def restore_from_trash(self, au: AuthedUser, nid: str) -> const.CodeEnum:
        resp = await self.es.update(
            index=self.index,
            id=nid,
            body={
                "doc": {
                    "inTrash": False,
                }
            },
            refresh=True,
        )
        if resp.meta.status != 200:
            logger.error(f"restore from trash failed {au.u.id=} {nid=}")
            return const.CodeEnum.OPERATION_FAILED
        return const.CodeEnum.OK

    async def restore_batch_from_trash(self, au: AuthedUser, nids: str) -> const.CodeEnum:
        resp = await helpers.async_bulk(
            client=self.es,
            actions=[
                {
                    "_op_type": "update",
                    "_index": get_settings().ES_INDEX_ALIAS,
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
            return const.CodeEnum.OPERATION_FAILED
        await self.refresh()
        return const.CodeEnum.OK

    async def disable(self, au: AuthedUser, nid: str) -> const.CodeEnum:
        resp = await self.es.update(
            index=self.index,
            id=nid,
            body={
                "doc": {
                    "disabled": True,
                }
            },
            refresh=True,
        )
        if resp.meta.status != 200:
            logger.error(f"disable failed {au.u.id=} {nid=}")
            return const.CodeEnum.OPERATION_FAILED
        return const.CodeEnum.OK

    async def enable(self, au: AuthedUser, nid: str) -> const.CodeEnum:
        resp = await self.es.update(
            index=self.index,
            id=nid,
            body={
                "doc": {
                    "disabled": False,
                }
            },
            refresh=True,
        )
        if resp.meta.status != 200:
            logger.error(f"enable failed {au.u.id=} {nid=}")
            return const.CodeEnum.OPERATION_FAILED
        return const.CodeEnum.OK

    async def delete(self, au: AuthedUser, nid: str) -> const.CodeEnum:
        doc = await self.es.get(
            index=self.index,
            id=nid,
        )
        if doc["_source"]["uid"] != au.u.id:
            logger.error(f"node not belong to user {au.u.id=} {nid=}")
            return const.CodeEnum.NODE_NOT_EXIST
        if not doc["_source"]["inTrash"]:
            logger.error(f"doc not in trash, deletion failed {au.u.id=} {nid=}")
            return const.CodeEnum.OPERATION_FAILED

        resp = await self.es.delete(
            index=self.index,
            id=nid,
            refresh=True,
        )
        if resp.meta.status != 201:
            logger.error(f"delete failed {au.u.id=} {nid=}")
            return const.CodeEnum.OPERATION_FAILED
        return const.CodeEnum.OK

    async def add_batch(self, au: AuthedUser, docs: List[SearchDoc]) -> const.CodeEnum:
        actions = []
        now = datetime.datetime.now(tz=utc)
        for doc in docs:
            d = doc.__dict__
            d["inTrash"] = False
            d["disabled"] = False
            d["createdAt"] = datetime2str(now)
            d["modifiedAt"] = d["createdAt"]
            d["uid"] = au.u.id
            nid = d.pop("nid")
            # insert a creation operation
            actions.append({
                "_op_type": "create",
                "_index": get_settings().ES_INDEX_ALIAS,
                "_id": nid,
                "_source": d
            })
            now = now + datetime.timedelta(seconds=0.001)
        return await self._batch_ops(actions, op_type="add", refresh=False)

    async def delete_batch(self, au: AuthedUser, nids: List[str]) -> const.CodeEnum:
        resp = await self.es.delete_by_query(
            index=self.index,
            body={
                "query": {
                    "bool": {
                        "must": [
                            {"ids": {"values": nids}},
                            {
                                "term": {
                                    "uid": au.u.id
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
            },
            refresh=True,
        )

        if resp.meta.status != 200:
            logger.error(f"delete batch failed, resp: {resp}")
            return const.CodeEnum.OPERATION_FAILED
        if resp.body["deleted"] != len(nids):
            logger.error(f"delete batch failed, resp: {resp}")
            return const.CodeEnum.OPERATION_FAILED
        return const.CodeEnum.OK

    async def force_delete_all(self, uid: str) -> const.CodeEnum:
        resp = await self.es.delete_by_query(
            index=self.index,
            body={
                "query": {
                    "bool": {
                        "must": [
                            {
                                "term": {
                                    "uid": uid
                                }
                            },

                        ]
                    }
                }
            },
            refresh=True,
        )
        if resp.meta.status != 200:
            logger.error(f"force delete all failed, resp: {resp}")
            return const.CodeEnum.OPERATION_FAILED
        return const.CodeEnum.OK

    async def update_batch(self, au: AuthedUser, docs: List[SearchDoc]) -> const.CodeEnum:
        actions = []
        now = datetime.datetime.now(tz=utc)
        for doc in docs:
            d = doc.__dict__
            d["modifiedAt"] = datetime2str(now)
            d["uid"] = au.u.id
            nid = d.pop("nid")
            actions.append({
                "_op_type": "update",
                "_index": get_settings().ES_INDEX_ALIAS,
                "_id": nid,
                "doc": d
            })
            now = now + datetime.timedelta(seconds=0.001)
        return await self._batch_ops(actions, op_type="update", refresh=False)

    async def batch_restore_docs(self, au: AuthedUser, docs: List[RestoreSearchDoc]) -> const.CodeEnum:
        actions = []
        for doc in docs:
            d = doc.__dict__
            d["createdAt"] = datetime2str(d["createdAt"])
            d["modifiedAt"] = datetime2str(d["modifiedAt"])
            d["uid"] = au.u.id
            nid = d.pop("nid")
            # insert a creation operation
            actions.append({
                "_op_type": "create",
                "_index": get_settings().ES_INDEX_ALIAS,
                "_id": nid,
                "_source": d
            })
        return await self._batch_ops(actions, "restore", refresh=True)

    async def _search(
            self,
            au: AuthedUser,
            query: str = "",
            sort_key: Literal[
                "createdAt", "modifiedAt", "title", "similarity"
            ] = None,
            reverse: bool = False,
            page: int = 0,
            page_size: int = 10,
            exclude_nids: Sequence[str] = None,
            with_stop_analyzer: bool = False,
    ) -> ObjectApiResponse[Any]:
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
        # select uid = au.u.id, disabled = false, inTrash = false
        query_dict: Dict[str, Any] = {
            "bool": {
                "must": [
                    {"constant_score": {"filter": {"term": {"uid": au.u.id}}}},
                    {"constant_score": {"filter": {"term": {"disabled": False}}}},
                    {"constant_score": {"filter": {"term": {"inTrash": False}}}},
                ]
            },
        }
        if query != "":
            q_lower = query.lower()
            analyzer = "search_stop_analyzer" if with_stop_analyzer else "ik_smart"
            # search q_lower on both title and body
            query_dict["bool"]["must"].append({
                "bool": {
                    "should": [
                        {
                            "match": {
                                "title": {
                                    "query": q_lower,
                                    "boost": 2,
                                    "analyzer": analyzer,
                                }
                            }
                        },
                        {
                            "match": {
                                "body": {
                                    "query": q_lower,
                                    "boost": 1,
                                    "analyzer": analyzer,
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
            index=self.index,
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
        return resp

    async def search(
            self,
            au: AuthedUser,
            query: str = "",
            sort_key: Literal[
                "createdAt", "modifiedAt", "title", "similarity"
            ] = None,
            reverse: bool = False,
            page: int = 0,
            limit: int = 10,
            exclude_nids: Sequence[str] = None,
    ) -> Tuple[List[SearchResult], int]:
        resp = await self._search(
            au=au,
            query=query,
            sort_key=sort_key,
            reverse=reverse,
            page=page,
            page_size=limit,
            exclude_nids=exclude_nids,
            with_stop_analyzer=False,
        )
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

    async def recommend(
            self,
            au: AuthedUser,
            content: str,
            max_return: int = 10,
            exclude_nids: int = None,
    ) -> List[SearchResult]:
        threshold = 3.
        resp = await self._search(
            au=au,
            query=content,
            sort_key="similarity",
            reverse=False,
            page=0,
            page_size=max_return,
            exclude_nids=exclude_nids,
            with_stop_analyzer=True,
        )
        hits = resp["hits"]["hits"]
        return [
            SearchResult(
                nid=hit["_id"],
                score=hit["_score"],
                titleHighlight=self.get_hl(hit, "title", first=True, default=hit["_source"]["title"]),
                bodyHighlights=self.get_hl(hit, "body", first=False, default=hit["_source"]["body"][:60] + "..."),
            ) for hit in hits if hit["_score"] is not None and hit["_score"] > threshold
        ]

    async def count_all(self) -> int:
        resp = await self.es.count(
            index=self.index,
            body={
                "query": {
                    "match_all": {}
                }
            })
        return resp["count"]

    async def refresh(self):
        await self.es.indices.refresh(index=self.index)

    async def _batch_ops(self, actions: List[dict], op_type: str, refresh: bool) -> const.CodeEnum:
        try:
            resp = await helpers.async_bulk(client=self.es, actions=actions)
        except helpers.BulkIndexError as e:
            logger.error(f"{op_type} batch failed, resp: {e.args[0]}")
            return const.CodeEnum.OPERATION_FAILED
        if resp[0] != len(actions):
            logger.error(f"{op_type} batch failed, resp: {resp}")
            return const.CodeEnum.OPERATION_FAILED
        if refresh:
            await self.refresh()
        return const.CodeEnum.OK

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
