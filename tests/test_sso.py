import unittest
from unittest.mock import patch

from fastapi import HTTPException

from retk.controllers import oauth
from retk.depend.sso import github
from tests import utils


class SSOTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        utils.set_env(".env.test.local")
        oauth.init_oauth_provider_map()

    @classmethod
    def tearDownClass(cls) -> None:
        utils.drop_env(".env.test.local")

    async def test_github(self):
        sso = github.GithubSSO(
            client_id="",
            client_secret="",
            redirect_uri="",
            allow_insecure_http=False,
            use_state=False,
            scope=None,
        )
        self.assertEqual("github", sso.provider)
        self.assertEqual({
            "authorization_endpoint": "https://github.com/login/oauth/authorize",
            "token_endpoint": "https://github.com/login/oauth/access_token",
            "userinfo_endpoint": "https://api.github.com/user",
        }, await sso.get_discovery_document())

    async def test_github_openid_from_response(self):
        sso = github.GithubSSO(
            client_id="",
            client_secret="",
            redirect_uri="",
            allow_insecure_http=False,
            use_state=False,
            scope=None,
        )
        open_id = await sso.openid_from_response({
            "email": "email",
            "id": "id",
            "login": "login",
            "avatar_url": "avatar_url",
        })
        self.assertEqual("id", open_id.id)
        self.assertEqual("github", open_id.provider)
        self.assertEqual("login", open_id.display_name)
        self.assertEqual("avatar_url", open_id.picture)
        self.assertEqual("email", open_id.email)

    @patch("retk.depend.sso.base.SSOBase.get_login_url")
    async def test_login_github(
            self,
            mock_get_login_url,
    ):
        mock_get_login_url.return_value = "https://github.com/"
        res = await oauth.login_provider("github")
        self.assertEqual("https://github.com/", res.uri.unicode_string())

    async def test_login_not_exist(self):
        with self.assertRaises(HTTPException):
            await oauth.login_provider("not_exist")
