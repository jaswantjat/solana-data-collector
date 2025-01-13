import os
import logging
from typing import Dict, List, Optional
import tweepy
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TwitterAPI:
    def __init__(self):
        self.api_key = os.getenv("TWITTER_API_KEY")
        self.api_secret = os.getenv("TWITTER_API_SECRET")
        self.access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        self.access_secret = os.getenv("TWITTER_ACCESS_SECRET")
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        
        # Initialize API client
        self.client = tweepy.Client(
            bearer_token=self.bearer_token,
            consumer_key=self.api_key,
            consumer_secret=self.api_secret,
            access_token=self.access_token,
            access_token_secret=self.access_secret
        )
        
    async def search_tweets(self, query: str, max_results: int = 100) -> List[Dict]:
        """Search for tweets matching query"""
        try:
            tweets = self.client.search_recent_tweets(
                query=query,
                max_results=max_results,
                tweet_fields=['created_at', 'public_metrics', 'entities']
            )
            
            return [self._format_tweet(tweet) for tweet in tweets.data] if tweets.data else []
            
        except Exception as e:
            logger.error(f"Error searching tweets: {str(e)}")
            return []
            
    async def get_user_tweets(self, username: str, max_results: int = 100) -> List[Dict]:
        """Get tweets from specific user"""
        try:
            user = self.client.get_user(username=username)
            if not user.data:
                return []
                
            tweets = self.client.get_users_tweets(
                id=user.data.id,
                max_results=max_results,
                tweet_fields=['created_at', 'public_metrics', 'entities']
            )
            
            return [self._format_tweet(tweet) for tweet in tweets.data] if tweets.data else []
            
        except Exception as e:
            logger.error(f"Error getting user tweets: {str(e)}")
            return []
            
    async def get_user_info(self, username: str) -> Dict:
        """Get user information"""
        try:
            user = self.client.get_user(
                username=username,
                user_fields=['created_at', 'public_metrics', 'description']
            )
            
            if not user.data:
                return {}
                
            return {
                'id': user.data.id,
                'username': user.data.username,
                'name': user.data.name,
                'created_at': user.data.created_at.isoformat(),
                'followers_count': user.data.public_metrics['followers_count'],
                'following_count': user.data.public_metrics['following_count'],
                'tweet_count': user.data.public_metrics['tweet_count'],
                'description': user.data.description
            }
            
        except Exception as e:
            logger.error(f"Error getting user info: {str(e)}")
            return {}
            
    async def analyze_token_mentions(self, token_address: str, days: int = 7) -> Dict:
        """Analyze token mentions on Twitter"""
        try:
            # Search for token address mentions
            tweets = await self.search_tweets(
                query=f"{token_address} -is:retweet",
                max_results=100
            )
            
            # Analyze mentions
            total_mentions = len(tweets)
            total_likes = sum(tweet['metrics']['like_count'] for tweet in tweets)
            total_retweets = sum(tweet['metrics']['retweet_count'] for tweet in tweets)
            
            # Calculate engagement rate
            engagement_rate = (total_likes + total_retweets) / total_mentions if total_mentions > 0 else 0
            
            return {
                'total_mentions': total_mentions,
                'total_likes': total_likes,
                'total_retweets': total_retweets,
                'engagement_rate': engagement_rate,
                'recent_tweets': tweets[:10]  # Return 10 most recent tweets
            }
            
        except Exception as e:
            logger.error(f"Error analyzing token mentions: {str(e)}")
            return {}
            
    def _format_tweet(self, tweet) -> Dict:
        """Format tweet data"""
        return {
            'id': tweet.id,
            'text': tweet.text,
            'created_at': tweet.created_at.isoformat(),
            'metrics': {
                'retweet_count': tweet.public_metrics['retweet_count'],
                'reply_count': tweet.public_metrics['reply_count'],
                'like_count': tweet.public_metrics['like_count'],
                'quote_count': tweet.public_metrics['quote_count']
            },
            'entities': tweet.entities if hasattr(tweet, 'entities') else {}
        }
