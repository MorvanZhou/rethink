"""Google SSO Login Helper
"""

from .base import DiscoveryDocument, OpenID, SSOBase, SSOLoginError
from ... import httpx_helper


class QQSSO(SSOBase):
    """Class providing login via Google OAuth"""

    discovery_url = "https://accounts.google.com/.well-known/openid-configuration"
    provider = "tencent"
    scope = ["openid", "email", "profile"]

    @classmethod
    async def openid_from_response(cls, response: dict) -> OpenID:
        """Return OpenID from user information provided by Google"""
        if response.get("email_verified"):
            return OpenID(
                email=response.get("email", ""),
                provider=cls.provider,
                id=response.get("sub"),
                first_name=response.get("given_name"),
                last_name=response.get("family_name"),
                display_name=response.get("name"),
                picture=response.get("picture"),
            )
        raise SSOLoginError(401, f"User {response.get('email')} is not verified with Google")

    async def get_discovery_document(self) -> DiscoveryDocument:
        """Get document containing handy urls"""
        response = await httpx_helper.get_async_client().get(self.discovery_url)
        content = response.json()
        return content
