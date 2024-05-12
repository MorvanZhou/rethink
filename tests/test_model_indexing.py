import os
import shutil
import unittest
from unittest.mock import patch, AsyncMock

from retk.depend.mongita import MongitaClientDisk
from retk.models.indexing import not_in_and_create_index


class TestModelIndexing(unittest.IsolatedAsyncioTestCase):
    @patch("retk.depend.mongita.collection.Collection.create_index", new_callable=AsyncMock)
    @patch("retk.depend.mongita.collection.Collection.index_information")
    async def test_not_in_and_create_index(
            self,
            mock_index_information,
            mock_create_index
    ):
        mock_index_information.return_value = {}
        mock_create_index.return_value = None

        async def case(keys, out_index):
            index = await not_in_and_create_index(
                coll=coll,
                index_info={},
                keys=keys,
                unique=True,
            )
            self.assertEqual(out_index, index)

        mongo_path = os.path.join("tmp", "mongo")
        os.makedirs(mongo_path, exist_ok=True)
        mongo = MongitaClientDisk(mongo_path)
        db = mongo["test_db"]
        coll = db["test_coll"]

        await case(["id"], "id_1")
        await case(["account", "source"], "account_1_source_1")
        await case([("uid", 1), ("id", -1)], "uid_1_id_-1")
        await case([("uid", 1), ("fid", -1)], "uid_1_fid_-1")
        await case(["recipientId", "read"], "recipientId_1_read_1")

        with self.assertRaises(ValueError):
            await case([["id"]], "id_1")

        shutil.rmtree(mongo_path)
        await mongo.close()
