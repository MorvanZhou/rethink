"""Facebook SSO Login Helper
"""

from .base import DiscoveryDocument, OpenID, SSOBase


class FacebookSSO(SSOBase):
    """Class providing login via Facebook OAuth"""

    provider = "facebook"
    base_url = "https://graph.facebook.com/v9.0"
    scope = ["email"]

    async def get_discovery_document(self) -> DiscoveryDocument:
        """Get document containing handy urls"""
        return {
            "authorization_endpoint": "https://www.facebook.com/v9.0/dialog/oauth",
            "token_endpoint": f"{self.base_url}/oauth/access_token",
            "userinfo_endpoint": f"{self.base_url}/me?fields=id,name,email,first_name,last_name,picture",
        }

    @classmethod
    async def openid_from_response(cls, response: dict) -> OpenID:
        """Return OpenID from user information provided by Facebook"""
        return OpenID(
            email=response.get("email", ""),
            first_name=response.get("first_name"),
            last_name=response.get("last_name"),
            display_name=response.get("name"),
            provider=cls.provider,
            id=response.get("id"),
            picture=response.get("picture", {}).get("data", {}).get("url", None),
        )
