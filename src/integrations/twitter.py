import tweepy
import logging
from typing import Dict, List, Optional
import os
from datetime import datetime, timedelta
from textblob import TextBlob

logger = logging.getLogger(__name__)

class TwitterAPI:
    def __init__(self):
        self.api_key = os.getenv("TWITTER_API_KEY")
        self.api_secret = os.getenv("TWITTER_API_SECRET")
        self.access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        self.access_secret = os.getenv("TWITTER_ACCESS_SECRET")
        self.client = self._init_client()
        
    def _init_client(self) -> tweepy.Client:
        """Initialize Twitter client"""
        try:
            return tweepy.Client(
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_secret
            )
        except Exception as e:
            logger.error(f"Error initializing Twitter client: {str(e)}")
            return None
            
    async def analyze_token_mentions(self, token_address: str) -> Dict:
        """Analyze Twitter mentions for a token"""
        try:
            # Search for tweets containing the token address
            query = f"{token_address} -is:retweet"
            tweets = self.client.search_recent_tweets(
                query=query,
                max_results=100,
                tweet_fields=["created_at", "public_metrics", "author_id"]
            )
            
            if not tweets.data:
                return self._empty_analysis()
                
            # Get user information for tweet authors
            user_ids = [tweet.author_id for tweet in tweets.data]
            users = self.client.get_users(ids=user_ids, user_fields=["public_metrics", "verified"])
            user_map = {user.id: user for user in users.data}
            
            return self._analyze_tweets(tweets.data, user_map)
            
        except Exception as e:
            logger.error(f"Error analyzing token mentions: {str(e)}")
            return self._empty_analysis()
            
    async def get_account_history(self, username: str) -> Dict:
        """Get account history including name changes"""
        try:
            user = self.client.get_user(
                username=username,
                user_fields=["created_at", "name", "description"]
            )
            
            if not user.data:
                return {}
                
            # Get user's tweets to analyze name changes
            tweets = self.client.get_users_tweets(
                id=user.data.id,
                max_results=100,
                tweet_fields=["created_at"]
            )
            
            return self._analyze_account_history(user.data, tweets.data if tweets.data else [])
            
        except Exception as e:
            logger.error(f"Error getting account history: {str(e)}")
            return {}
            
    def _analyze_tweets(self, tweets: List, users: Dict) -> Dict:
        """Analyze tweets and calculate metrics"""
        try:
            total_mentions = len(tweets)
            sentiment_scores = []
            influencer_mentions = 0
            engagement = 0
            
            for tweet in tweets:
                # Calculate sentiment
                blob = TextBlob(tweet.text)
                sentiment_scores.append(blob.sentiment.polarity)
                
                # Check if author is an influencer
                user = users.get(tweet.author_id)
                if user:
                    followers = user.public_metrics["followers_count"]
                    if followers > 10000 and user.verified:
                        influencer_mentions += 1
                        
                # Calculate engagement
                metrics = tweet.public_metrics
                engagement += (
                    metrics["retweet_count"] * 2 +
                    metrics["reply_count"] * 1.5 +
                    metrics["like_count"]
                )
                
            return {
                "total_mentions": total_mentions,
                "average_sentiment": sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0,
                "influencer_mentions": influencer_mentions,
                "engagement_score": engagement / total_mentions if total_mentions > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error analyzing tweets: {str(e)}")
            return self._empty_analysis()
            
    def _analyze_account_history(self, user: Dict, tweets: List) -> Dict:
        """Analyze account history for suspicious patterns"""
        try:
            # Extract name from tweet history to detect changes
            name_changes = []
            current_name = user.name
            
            for tweet in tweets:
                if hasattr(tweet, "author") and tweet.author.name != current_name:
                    name_changes.append({
                        "from": current_name,
                        "to": tweet.author.name,
                        "date": tweet.created_at
                    })
                    current_name = tweet.author.name
                    
            return {
                "username": user.username,
                "created_at": user.created_at,
                "name_changes": name_changes,
                "name_change_count": len(name_changes),
                "account_age_days": (datetime.now() - user.created_at).days
            }
            
        except Exception as e:
            logger.error(f"Error analyzing account history: {str(e)}")
            return {}
            
    def _empty_analysis(self) -> Dict:
        """Return empty analysis structure"""
        return {
            "total_mentions": 0,
            "average_sentiment": 0,
            "influencer_mentions": 0,
            "engagement_score": 0
        }
