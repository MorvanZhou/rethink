import datetime
from typing import List, Tuple

from bson.tz_util import utc
from elasticsearch import AsyncElasticsearch
from elasticsearch import helpers

from rethink.config import get_settings
from rethink.models.search.engine import BaseEngine, SearchDoc, SearchResult


def get_utc_now() -> str:
    now = datetime.datetime.now(tz=utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class ESSearcher(BaseEngine):
    es: AsyncElasticsearch
    index_name = "nodes"
    properties = {
        "uid": {
            "type": "keyword"
        },
        "title": {
            "type": "keyword"
        },
        "md": {
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
                "tokenizer": "ik_max_word"
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

        if not await self.es.indices.exists(index=self.index_name):
            # install ik plugin: https://github.com/medcl/elasticsearch-analysis-ik
            await self.es.indices.create(
                index=self.index_name,
                body={
                    "settings": {
                        "index": {
                            "number_of_shards": 1,
                            "number_of_replicas": 0,
                            "refresh_interval": "5s",
                        },
                        "analysis": self.analysis,
                    },
                    "mappings": {
                        "properties": self.properties,
                    }
                }
            )

    async def drop(self):
        self.connect()
        if await self.es.indices.exists(index=self.index_name):
            await self.es.indices.delete(index=self.index_name)

    async def add(self, uid: str, doc: SearchDoc):
        now = get_utc_now()
        await self.es.index(
            index=self.index_name,
            document={
                "uid": uid,
                "title": doc.title,
                "md": doc.md,
                "modifiedAt": now,
                "createdAt": now,
            },
            id=doc.nid,
        )

    async def update(self, uid: str, doc: SearchDoc):
        now = get_utc_now()
        await self.es.update(
            index=self.index_name,
            id=doc.nid,
            body={
                "doc": {
                    "uid": uid,
                    "title": doc.title,
                    "md": doc.md,
                    "modifiedAt": now,
                }
            }
        )

    async def delete(self, uid: str, nid: str):
        await self.es.delete(
            index=self.index_name,
            id=nid,
        )

    async def add_batch(self, uid: str, docs: List[SearchDoc]):
        actions = []
        for doc in docs:
            d = doc.__dict__
            d["createdAt"] = get_utc_now()
            d["modifiedAt"] = d["createdAt"]
            d["uid"] = uid
            nid = d.pop("nid")
            # insert a creation operation
            actions.append({
                "_op_type": "create",
                "_index": self.index_name,
                "_id": nid,
                "_source": d
            })
        resp = await helpers.async_bulk(client=self.es, actions=actions)
        if resp[0] != len(actions):
            raise ValueError(f"add batch failed, resp: {resp}")

    async def delete_batch(self, uid: str, nids: List[str]):
        resp = await helpers.async_bulk(
            client=self.es,
            actions=[
                {
                    "_op_type": "delete",
                    "_index": self.index_name,
                    "_id": nid,
                }
                for nid in nids
            ]
        )
        if resp[0] != len(nids):
            raise ValueError(f"delete batch failed, resp: {resp}")

    async def update_batch(self, uid: str, docs: List[SearchDoc]):
        actions = []
        for doc in docs:
            d = doc.__dict__
            d["modifiedAt"] = get_utc_now()
            d["uid"] = uid
            nid = d.pop("nid")
            actions.append({
                "_op_type": "update",
                "_index": self.index_name,
                "_id": nid,
                "doc": d
            })
        resp = await helpers.async_bulk(client=self.es, actions=actions)
        if resp[0] != len(actions):
            raise ValueError(f"update batch failed, resp: {resp}")

    async def search(
            self,
            uid: str,
            query: str,
            sort_key: str = None,
            reverse: bool = False,
            page: int = 1,
            page_size: int = 10,
    ) -> Tuple[List[SearchResult], int]:
        if page < 1:
            raise ValueError("page must >= 1")
        if sort_key is None:
            sort_key = "_score"
        sort = {sort_key: {"order": "desc" if reverse else "asc"}}
        if sort_key in ["createdAt", "modifiedAt"]:
            sort[sort_key]["format"] = "strict_date_optional_time_nanos"
        elif sort_key in ["_score", "_id", "title"]:
            pass
        else:
            raise ValueError(f"sort_key {sort_key} not supported")

        resp = await self.es.search(
            index=self.index_name,
            body={
                "query": {"bool": {"must": [
                    {
                        "match": {
                            "md": query
                        }
                    },
                    {
                        "match": {
                            "uid": uid
                        }
                    }
                ]}},
                "sort": [sort],
                "from": (page - 1) * page_size,
                "size": page_size,
                "highlight": {
                    "pre_tags": [
                        f"<{self.hl_tag_name} class=\"{self.hl_class_name} {self.hl_term_prefix}{i}\">"
                        for i in range(5)
                    ],
                    "post_tags": [f"</{self.hl_tag_name}>" for _ in range(5)],
                    "fields": {
                        "md": {}
                    }
                },
            })
        hits = resp["hits"]["hits"]
        total = resp["hits"]["total"]["value"]
        return [
            SearchResult(
                nid=hit["_id"],
                title=hit["_source"]["title"],
                md=hit["_source"]["md"],
                score=hit["_score"],
                highlights=hit["highlight"]["md"][0],
                modifiedAt=hit["_source"]["modifiedAt"],
                createdAt=hit["_source"]["createdAt"],
            )
            for hit in hits], total

    async def refresh(self):
        await self.es.indices.refresh(index=self.index_name)

    async def close(self):
        await self.es.close()
        del self.es
