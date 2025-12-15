"""
Data ingestion fetchers for various social media platforms.
Each fetcher implements profile and post retrieval using official APIs where available.

IMPORTANT: Always respect platform Terms of Service and rate limits.
Some platforms require OAuth authentication or app approval.
"""
import os
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from datetime import datetime

import requests

from app.schemas.data_ingestion import Post, UserProfile

logger = logging.getLogger(__name__)


class BaseFetcher(ABC):
    """Abstract base class for all platform fetchers."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "SentimentAnalyzer/1.0"
        })

    @abstractmethod
    def fetch_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Fetch user profile information."""
        pass

    @abstractmethod
    def fetch_posts(self, user_id: str, limit: int = 50) -> List[Post]:
        """Fetch posts/statuses from a user."""
        pass

    def _safe_request(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """Make a safe HTTP request with error handling."""
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None


class LinkedInFetcher(BaseFetcher):
    """
    LinkedIn data fetcher using LinkedIn API.
    Requires OAuth 2.0 access token with appropriate scopes.
    See: https://docs.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow
    """

    BASE_URL = "https://api.linkedin.com/v2"

    def __init__(self):
        super().__init__()
        self.access_token = os.getenv("LINKEDIN_TOKEN")
        if self.access_token:
            self.session.headers.update({
                "Authorization": f"Bearer {self.access_token}",
                "X-Restli-Protocol-Version": "2.0.0",
            })

    def fetch_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        Fetch LinkedIn profile. Requires r_liteprofile or r_fullprofile scope.
        user_id can be 'me' for authenticated user or a member URN.
        """
        if not self.access_token:
            logger.warning("LinkedIn token not configured")
            return None

        # Fetch basic profile
        url = f"{self.BASE_URL}/me"
        resp = self._safe_request("GET", url)
        if not resp:
            return None

        data = resp.json()
        
        # Fetch email (requires r_emailaddress scope)
        email = None
        email_resp = self._safe_request(
            "GET",
            f"{self.BASE_URL}/emailAddress?q=members&projection=(elements*(handle~))"
        )
        if email_resp:
            email_data = email_resp.json()
            elements = email_data.get("elements", [])
            if elements:
                email = elements[0].get("handle~", {}).get("emailAddress")

        return UserProfile(
            platform="linkedin",
            user_id=data.get("id", user_id),
            username=None,  # LinkedIn doesn't expose public username via API
            name=f"{data.get('localizedFirstName', '')} {data.get('localizedLastName', '')}".strip(),
            email=email,
            phone=None,
            dob=None,
            location=data.get("location", {}).get("name"),
        )

    def fetch_posts(self, user_id: str, limit: int = 50) -> List[Post]:
        """
        Fetch LinkedIn posts/shares. Requires w_member_social scope.
        """
        if not self.access_token:
            logger.warning("LinkedIn token not configured")
            return []

        posts: List[Post] = []
        url = f"{self.BASE_URL}/ugcPosts?q=authors&authors=List(urn:li:person:{user_id})&count={limit}"
        
        resp = self._safe_request("GET", url)
        if not resp:
            return posts

        data = resp.json()
        for item in data.get("elements", []):
            text = ""
            specific_content = item.get("specificContent", {})
            share_content = specific_content.get("com.linkedin.ugc.ShareContent", {})
            share_commentary = share_content.get("shareCommentary", {})
            text = share_commentary.get("text", "")

            posts.append(Post(
                id=item.get("id", ""),
                platform="linkedin",
                author=user_id,
                author_id=item.get("author", ""),
                text=text,
                timestamp=datetime.fromtimestamp(
                    item.get("created", {}).get("time", 0) / 1000
                ).isoformat() if item.get("created") else None,
                url=f"https://www.linkedin.com/feed/update/{item.get('id', '')}",
            ))

        return posts


class FacebookFetcher(BaseFetcher):
    """
    Facebook/Meta Graph API fetcher.
    Requires access token with appropriate permissions.
    See: https://developers.facebook.com/docs/graph-api/
    """

    BASE_URL = "https://graph.facebook.com/v18.0"

    def __init__(self):
        super().__init__()
        self.access_token = os.getenv("FACEBOOK_TOKEN")

    def fetch_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        Fetch Facebook profile. user_id can be 'me' for authenticated user.
        Requires user_profile permission.
        """
        if not self.access_token:
            logger.warning("Facebook token not configured")
            return None

        fields = "id,name,email,birthday,location"
        url = f"{self.BASE_URL}/{user_id}?fields={fields}&access_token={self.access_token}"
        
        resp = self._safe_request("GET", url)
        if not resp:
            return None

        data = resp.json()
        return UserProfile(
            platform="facebook",
            user_id=data.get("id", user_id),
            username=None,
            name=data.get("name"),
            email=data.get("email"),
            phone=None,
            dob=data.get("birthday"),
            location=data.get("location", {}).get("name") if isinstance(data.get("location"), dict) else None,
        )

    def fetch_posts(self, user_id: str, limit: int = 50) -> List[Post]:
        """
        Fetch Facebook posts. Requires user_posts permission.
        """
        if not self.access_token:
            logger.warning("Facebook token not configured")
            return []

        posts: List[Post] = []
        fields = "id,message,created_time,permalink_url"
        url = f"{self.BASE_URL}/{user_id}/posts?fields={fields}&limit={limit}&access_token={self.access_token}"
        
        resp = self._safe_request("GET", url)
        if not resp:
            return posts

        data = resp.json()
        for item in data.get("data", []):
            if not item.get("message"):
                continue
            posts.append(Post(
                id=item.get("id", ""),
                platform="facebook",
                author=user_id,
                author_id=user_id,
                text=item.get("message", ""),
                timestamp=item.get("created_time"),
                url=item.get("permalink_url"),
            ))

        return posts


class TwitterFetcher(BaseFetcher):
    """
    Twitter/X API v2 fetcher.
    Requires Bearer Token for most endpoints.
    See: https://developer.twitter.com/en/docs/twitter-api
    """

    BASE_URL = "https://api.twitter.com/2"

    def __init__(self):
        super().__init__()
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        if self.bearer_token:
            self.session.headers.update({
                "Authorization": f"Bearer {self.bearer_token}"
            })

    def fetch_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        Fetch Twitter user profile by username or ID.
        """
        if not self.bearer_token:
            logger.warning("Twitter bearer token not configured")
            return None

        # Determine if user_id is numeric (ID) or username
        if user_id.isdigit():
            url = f"{self.BASE_URL}/users/{user_id}"
        else:
            url = f"{self.BASE_URL}/users/by/username/{user_id}"

        params = {
            "user.fields": "id,name,username,location,description,created_at,public_metrics"
        }
        
        resp = self._safe_request("GET", url, params=params)
        if not resp:
            return None

        data = resp.json().get("data", {})
        return UserProfile(
            platform="twitter",
            user_id=data.get("id", user_id),
            username=data.get("username"),
            name=data.get("name"),
            email=None,  # Not available via API
            phone=None,
            dob=None,
            location=data.get("location"),
        )

    def fetch_posts(self, user_id: str, limit: int = 50) -> List[Post]:
        """
        Fetch tweets from a user. Max 100 per request.
        """
        if not self.bearer_token:
            logger.warning("Twitter bearer token not configured")
            return []

        posts: List[Post] = []
        
        # Get user ID if username provided
        if not user_id.isdigit():
            profile = self.fetch_user_profile(user_id)
            if profile:
                user_id = profile.user_id
            else:
                return posts

        url = f"{self.BASE_URL}/users/{user_id}/tweets"
        params = {
            "max_results": min(limit, 100),
            "tweet.fields": "id,text,created_at,author_id"
        }
        
        resp = self._safe_request("GET", url, params=params)
        if not resp:
            return posts

        data = resp.json()
        for item in data.get("data", []):
            posts.append(Post(
                id=item.get("id", ""),
                platform="twitter",
                author=user_id,
                author_id=item.get("author_id", user_id),
                text=item.get("text", ""),
                timestamp=item.get("created_at"),
                url=f"https://twitter.com/i/status/{item.get('id', '')}",
            ))

        return posts


class InstagramFetcher(BaseFetcher):
    """
    Instagram Graph API fetcher (for Business/Creator accounts).
    Requires Facebook access token with instagram_basic permission.
    See: https://developers.facebook.com/docs/instagram-api/
    """

    BASE_URL = "https://graph.facebook.com/v18.0"

    def __init__(self):
        super().__init__()
        self.access_token = os.getenv("INSTAGRAM_TOKEN")

    def fetch_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        Fetch Instagram Business/Creator account profile.
        """
        if not self.access_token:
            logger.warning("Instagram token not configured")
            return None

        fields = "id,username,name,biography"
        url = f"{self.BASE_URL}/{user_id}?fields={fields}&access_token={self.access_token}"
        
        resp = self._safe_request("GET", url)
        if not resp:
            return None

        data = resp.json()
        return UserProfile(
            platform="instagram",
            user_id=data.get("id", user_id),
            username=data.get("username"),
            name=data.get("name"),
            email=None,
            phone=None,
            dob=None,
            location=None,
        )

    def fetch_posts(self, user_id: str, limit: int = 50) -> List[Post]:
        """
        Fetch Instagram media posts.
        """
        if not self.access_token:
            logger.warning("Instagram token not configured")
            return []

        posts: List[Post] = []
        fields = "id,caption,timestamp,permalink,username"
        url = f"{self.BASE_URL}/{user_id}/media?fields={fields}&limit={limit}&access_token={self.access_token}"
        
        resp = self._safe_request("GET", url)
        if not resp:
            return posts

        data = resp.json()
        for item in data.get("data", []):
            caption = item.get("caption", "")
            if not caption:
                continue
            posts.append(Post(
                id=item.get("id", ""),
                platform="instagram",
                author=item.get("username", user_id),
                author_id=user_id,
                text=caption,
                timestamp=item.get("timestamp"),
                url=item.get("permalink"),
            ))

        return posts


class ThreadsFetcher(BaseFetcher):
    """
    Threads API fetcher (Meta's text-based platform).
    Uses the Threads API which is similar to Instagram Graph API.
    See: https://developers.facebook.com/docs/threads/
    """

    BASE_URL = "https://graph.threads.net/v1.0"

    def __init__(self):
        super().__init__()
        self.access_token = os.getenv("THREADS_TOKEN")

    def fetch_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        Fetch Threads user profile.
        """
        if not self.access_token:
            logger.warning("Threads token not configured")
            return None

        fields = "id,username,name,threads_profile_picture_url,threads_biography"
        url = f"{self.BASE_URL}/{user_id}?fields={fields}&access_token={self.access_token}"
        
        resp = self._safe_request("GET", url)
        if not resp:
            return None

        data = resp.json()
        return UserProfile(
            platform="threads",
            user_id=data.get("id", user_id),
            username=data.get("username"),
            name=data.get("name"),
            email=None,
            phone=None,
            dob=None,
            location=None,
        )

    def fetch_posts(self, user_id: str, limit: int = 50) -> List[Post]:
        """
        Fetch Threads posts.
        """
        if not self.access_token:
            logger.warning("Threads token not configured")
            return []

        posts: List[Post] = []
        fields = "id,text,timestamp,permalink,username"
        url = f"{self.BASE_URL}/{user_id}/threads?fields={fields}&limit={limit}&access_token={self.access_token}"
        
        resp = self._safe_request("GET", url)
        if not resp:
            return posts

        data = resp.json()
        for item in data.get("data", []):
            text = item.get("text", "")
            if not text:
                continue
            posts.append(Post(
                id=item.get("id", ""),
                platform="threads",
                author=item.get("username", user_id),
                author_id=user_id,
                text=text,
                timestamp=item.get("timestamp"),
                url=item.get("permalink"),
            ))

        return posts


class TelegramFetcher(BaseFetcher):
    """
    Telegram Bot API fetcher for group messages.
    Requires a bot token and the bot must be added to the group.
    See: https://core.telegram.org/bots/api
    """

    BASE_URL = "https://api.telegram.org"

    def __init__(self):
        super().__init__()
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    def _api_url(self, method: str) -> str:
        return f"{self.BASE_URL}/bot{self.bot_token}/{method}"

    def fetch_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        Fetch Telegram user info. Limited information available via Bot API.
        """
        if not self.bot_token:
            logger.warning("Telegram bot token not configured")
            return None

        # Bot API doesn't directly support fetching arbitrary user profiles
        # This works only for users who have interacted with the bot
        url = self._api_url("getChat")
        params = {"chat_id": user_id}
        
        resp = self._safe_request("GET", url, params=params)
        if not resp:
            return None

        result = resp.json()
        if not result.get("ok"):
            return None

        data = result.get("result", {})
        return UserProfile(
            platform="telegram",
            user_id=str(data.get("id", user_id)),
            username=data.get("username"),
            name=f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
            email=None,
            phone=None,
            dob=None,
            location=None,
        )

    def fetch_posts(self, user_id: str, limit: int = 50) -> List[Post]:
        """
        Fetch messages from a Telegram group/channel.
        user_id should be the chat_id of the group.
        Note: Bot must be admin to access message history.
        """
        if not self.bot_token:
            logger.warning("Telegram bot token not configured")
            return []

        posts: List[Post] = []
        
        # getUpdates only returns recent messages for the bot
        # For full history, you need to use MTProto API (pyrogram/telethon)
        url = self._api_url("getUpdates")
        params = {"limit": limit, "allowed_updates": ["message", "channel_post"]}
        
        resp = self._safe_request("GET", url, params=params)
        if not resp:
            return posts

        result = resp.json()
        if not result.get("ok"):
            return posts

        for update in result.get("result", []):
            message = update.get("message") or update.get("channel_post")
            if not message:
                continue
            
            # Filter by chat_id if specified
            chat_id = str(message.get("chat", {}).get("id", ""))
            if user_id and chat_id != str(user_id):
                continue

            text = message.get("text", "")
            if not text:
                continue

            from_user = message.get("from", {})
            posts.append(Post(
                id=str(message.get("message_id", "")),
                platform="telegram",
                author=from_user.get("username") or f"{from_user.get('first_name', '')} {from_user.get('last_name', '')}".strip(),
                author_id=str(from_user.get("id", "")),
                text=text,
                timestamp=datetime.fromtimestamp(message.get("date", 0)).isoformat() if message.get("date") else None,
                url=None,
            ))

        return posts[:limit]


class WhatsAppFetcher(BaseFetcher):
    """
    WhatsApp Business API fetcher.
    Requires WhatsApp Business API access through Meta.
    See: https://developers.facebook.com/docs/whatsapp/cloud-api/
    
    Note: WhatsApp API is primarily for sending messages, not fetching history.
    Message history retrieval is limited and requires webhook integration.
    """

    BASE_URL = "https://graph.facebook.com/v18.0"

    def __init__(self):
        super().__init__()
        self.access_token = os.getenv("WHATSAPP_API_KEY")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

    def fetch_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        WhatsApp doesn't provide user profile fetching.
        user_id is expected to be a phone number.
        """
        if not self.access_token:
            logger.warning("WhatsApp API key not configured")
            return None

        # WhatsApp API doesn't support fetching user profiles
        # We can only return what we know from the phone number
        return UserProfile(
            platform="whatsapp",
            user_id=user_id,
            username=None,
            name=None,
            email=None,
            phone=user_id,  # Phone number is the identifier
            dob=None,
            location=None,
        )

    def fetch_posts(self, user_id: str, limit: int = 50) -> List[Post]:
        """
        WhatsApp Cloud API doesn't support fetching message history.
        Messages must be captured via webhooks in real-time.
        
        This is a placeholder - implement webhook handler separately.
        """
        if not self.access_token:
            logger.warning("WhatsApp API key not configured")
            return []

        # WhatsApp doesn't support fetching historical messages via API
        # You need to:
        # 1. Set up a webhook endpoint
        # 2. Configure it in Meta Business settings
        # 3. Store incoming messages in your database
        # 4. Query your database here
        
        logger.info(
            "WhatsApp message history requires webhook integration. "
            "See: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/"
        )
        return []


# Factory function to get the appropriate fetcher
def get_fetcher(platform: str) -> Optional[BaseFetcher]:
    """
    Factory function to get the appropriate fetcher for a platform.
    
    Args:
        platform: One of 'linkedin', 'facebook', 'twitter', 'instagram', 
                  'threads', 'telegram', 'whatsapp'
    
    Returns:
        Fetcher instance or None if platform is not supported
    """
    fetchers = {
        "linkedin": LinkedInFetcher,
        "facebook": FacebookFetcher,
        "twitter": TwitterFetcher,
        "instagram": InstagramFetcher,
        "threads": ThreadsFetcher,
        "telegram": TelegramFetcher,
        "whatsapp": WhatsAppFetcher,
    }
    
    fetcher_class = fetchers.get(platform.lower())
    if fetcher_class:
        return fetcher_class()
    return None


# Convenience function to fetch from all platforms
def fetch_all_posts(user_ids: Dict[str, str], limit: int = 50) -> List[Post]:
    """
    Fetch posts from multiple platforms.
    
    Args:
        user_ids: Dict mapping platform name to user_id
                  e.g., {"twitter": "elonmusk", "facebook": "me"}
        limit: Max posts per platform
    
    Returns:
        Combined list of posts from all platforms
    """
    all_posts: List[Post] = []
    
    for platform, user_id in user_ids.items():
        fetcher = get_fetcher(platform)
        if fetcher:
            try:
                posts = fetcher.fetch_posts(user_id, limit)
                all_posts.extend(posts)
                logger.info(f"Fetched {len(posts)} posts from {platform}")
            except Exception as e:
                logger.error(f"Error fetching from {platform}: {e}")
    
    return all_posts
