import unittest

from rethink import config
from rethink.sso.github import GithubSSO


class SSOTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        config.get_settings.cache_clear()

    @classmethod
    def tearDownClass(cls) -> None:
        config.get_settings.cache_clear()

    async def test_github(self):
        sso = GithubSSO(
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
        sso = GithubSSO(
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
