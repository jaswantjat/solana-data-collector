import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import json
from pathlib import Path
import tweepy
from textblob import TextBlob
import re
from collections import defaultdict

from ..integrations.helius import HeliusAPI

logger = logging.getLogger(__name__)

class SocialAnalysis:
    def __init__(self):
        self.helius = HeliusAPI()
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        self.social_data_file = self.data_dir / "social_data.json"
        self.notable_wallets_file = self.data_dir / "notable_wallets.json"
        
        # Initialize Twitter API
        self.twitter_api = self._init_twitter_api()
        
        self._load_data()
        
    def _init_twitter_api(self) -> Optional[tweepy.API]:
        """Initialize Twitter API connection"""
        try:
            auth = tweepy.OAuthHandler(
                self._get_env("TWITTER_API_KEY"),
                self._get_env("TWITTER_API_SECRET")
            )
            auth.set_access_token(
                self._get_env("TWITTER_ACCESS_TOKEN"),
                self._get_env("TWITTER_ACCESS_SECRET")
            )
            return tweepy.API(auth)
        except Exception as e:
            logger.error(f"Error initializing Twitter API: {str(e)}")
            return None
            
    def _get_env(self, key: str) -> str:
        """Get environment variable"""
        import os
        return os.getenv(key, "")
        
    def _load_data(self):
        """Load data from files"""
        try:
            if self.social_data_file.exists():
                with open(self.social_data_file, 'r') as f:
                    self.social_data = json.load(f)
            else:
                self.social_data = {"mentions": {}, "sentiment": {}, "history": {}}
                self._save_social_data()

            if self.notable_wallets_file.exists():
                with open(self.notable_wallets_file, 'r') as f:
                    self.notable_wallets = json.load(f)
            else:
                self.notable_wallets = {"wallets": [], "interactions": {}}
                self._save_notable_wallets()
                
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            self.social_data = {"mentions": {}, "sentiment": {}, "history": {}}
            self.notable_wallets = {"wallets": [], "interactions": {}}

    def _save_social_data(self):
        with open(self.social_data_file, 'w') as f:
            json.dump(self.social_data, f, indent=2)

    def _save_notable_wallets(self):
        with open(self.notable_wallets_file, 'w') as f:
            json.dump(self.notable_wallets, f, indent=2)

    async def analyze_social_presence(self, token_address: str, project_twitter: Optional[str] = None) -> Dict:
        """Analyze social media presence and sentiment"""
        try:
            # Get Twitter mentions
            mentions = await self._track_mentions(token_address, project_twitter)
            
            # Analyze sentiment
            sentiment = self._analyze_sentiment(mentions)
            
            # Track notable wallet interactions
            notable_interactions = await self._track_notable_interactions(token_address)
            
            # Analyze project history
            project_history = await self._analyze_project_history(token_address, project_twitter)
            
            # Update social data
            current_time = datetime.now().isoformat()
            if token_address not in self.social_data["history"]:
                self.social_data["history"][token_address] = []
            
            self.social_data["history"][token_address].append({
                "timestamp": current_time,
                "mentions": len(mentions),
                "sentiment": sentiment["overall_sentiment"],
                "notable_interactions": len(notable_interactions)
            })
            
            self._save_social_data()
            
            return {
                "token_address": token_address,
                "mentions_analysis": mentions,
                "sentiment_analysis": sentiment,
                "notable_interactions": notable_interactions,
                "project_history": project_history,
                "timestamp": current_time
            }

        except Exception as e:
            logger.error(f"Error analyzing social presence for {token_address}: {str(e)}")
            return self._create_empty_analysis(token_address)

    async def _track_mentions(self, token_address: str, project_twitter: Optional[str] = None) -> Dict:
        """Track contract address mentions on Twitter"""
        try:
            if not self.twitter_api:
                return {}

            mentions = []
            search_terms = [token_address]
            if project_twitter:
                search_terms.append(f"@{project_twitter}")

            for term in search_terms:
                tweets = self.twitter_api.search_tweets(
                    q=term,
                    lang="en",
                    count=100,
                    result_type="recent"
                )
                
                for tweet in tweets:
                    mentions.append({
                        "text": tweet.text,
                        "user": tweet.user.screen_name,
                        "followers": tweet.user.followers_count,
                        "created_at": tweet.created_at.isoformat(),
                        "retweets": tweet.retweet_count,
                        "likes": tweet.favorite_count
                    })

            # Group by time periods
            hourly = defaultdict(int)
            daily = defaultdict(int)
            
            for mention in mentions:
                created = datetime.fromisoformat(mention["created_at"])
                hour = created.strftime("%Y-%m-%d %H:00")
                day = created.strftime("%Y-%m-%d")
                
                hourly[hour] += 1
                daily[day] += 1

            return {
                "total_mentions": len(mentions),
                "unique_users": len(set(m["user"] for m in mentions)),
                "total_reach": sum(m["followers"] for m in mentions),
                "hourly_mentions": dict(hourly),
                "daily_mentions": dict(daily),
                "top_mentions": sorted(mentions, 
                                    key=lambda x: x["followers"] * (x["retweets"] + x["likes"]),
                                    reverse=True)[:10]
            }

        except Exception as e:
            logger.error(f"Error tracking mentions: {str(e)}")
            return {}

    def _analyze_sentiment(self, mentions: Dict) -> Dict:
        """Analyze sentiment of social media mentions"""
        try:
            if not mentions or "top_mentions" not in mentions:
                return {}

            sentiments = []
            for mention in mentions["top_mentions"]:
                analysis = TextBlob(mention["text"])
                sentiments.append({
                    "text": mention["text"],
                    "polarity": analysis.sentiment.polarity,
                    "subjectivity": analysis.sentiment.subjectivity,
                    "reach": mention["followers"] * (mention["retweets"] + mention["likes"])
                })

            # Calculate weighted sentiment
            total_reach = sum(s["reach"] for s in sentiments)
            if total_reach > 0:
                weighted_sentiment = sum(s["polarity"] * s["reach"] for s in sentiments) / total_reach
            else:
                weighted_sentiment = 0

            # Categorize sentiments
            categories = {
                "positive": len([s for s in sentiments if s["polarity"] > 0.2]),
                "neutral": len([s for s in sentiments if -0.2 <= s["polarity"] <= 0.2]),
                "negative": len([s for s in sentiments if s["polarity"] < -0.2])
            }

            return {
                "overall_sentiment": weighted_sentiment,
                "sentiment_categories": categories,
                "average_subjectivity": sum(s["subjectivity"] for s in sentiments) / len(sentiments) if sentiments else 0,
                "detailed_sentiments": sentiments
            }

        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return {}

    async def _track_notable_interactions(self, token_address: str) -> List[Dict]:
        """Track interactions from notable wallets"""
        try:
            # Get token transactions
            transactions = await self.helius.get_token_transactions(token_address)
            if not transactions:
                return []

            notable_interactions = []
            for tx in transactions:
                from_address = tx.get("from")
                to_address = tx.get("to")
                
                # Check if either address is notable
                notable_from = from_address in self.notable_wallets["wallets"]
                notable_to = to_address in self.notable_wallets["wallets"]
                
                if notable_from or notable_to:
                    interaction = {
                        "transaction": tx.get("signature"),
                        "timestamp": tx.get("timestamp"),
                        "amount": float(tx.get("amount", 0)),
                        "type": tx.get("type")
                    }
                    
                    if notable_from:
                        interaction["notable_wallet"] = from_address
                        interaction["direction"] = "from"
                    else:
                        interaction["notable_wallet"] = to_address
                        interaction["direction"] = "to"
                        
                    notable_interactions.append(interaction)
                    
                    # Update interaction history
                    if interaction["notable_wallet"] not in self.notable_wallets["interactions"]:
                        self.notable_wallets["interactions"][interaction["notable_wallet"]] = []
                    self.notable_wallets["interactions"][interaction["notable_wallet"]].append({
                        "token": token_address,
                        "timestamp": interaction["timestamp"],
                        "type": interaction["type"]
                    })

            self._save_notable_wallets()
            return notable_interactions

        except Exception as e:
            logger.error(f"Error tracking notable interactions: {str(e)}")
            return []

    async def _analyze_project_history(self, token_address: str, project_twitter: Optional[str] = None) -> Dict:
        """Analyze project account history"""
        try:
            if not self.twitter_api or not project_twitter:
                return {}

            # Get project Twitter account
            user = self.twitter_api.get_user(screen_name=project_twitter)
            
            # Get recent tweets
            tweets = self.twitter_api.user_timeline(
                screen_name=project_twitter,
                count=100,
                include_rts=False
            )
            
            # Analyze engagement
            engagement = []
            for tweet in tweets:
                engagement.append({
                    "timestamp": tweet.created_at.isoformat(),
                    "retweets": tweet.retweet_count,
                    "likes": tweet.favorite_count,
                    "replies": tweet.reply_count if hasattr(tweet, 'reply_count') else 0
                })

            # Calculate engagement metrics
            avg_engagement = sum(e["retweets"] + e["likes"] + e["replies"] 
                               for e in engagement) / len(engagement) if engagement else 0

            return {
                "account_age_days": (datetime.now() - user.created_at).days,
                "followers": user.followers_count,
                "following": user.friends_count,
                "total_tweets": user.statuses_count,
                "average_engagement": avg_engagement,
                "engagement_history": engagement,
                "verified": user.verified if hasattr(user, 'verified') else False
            }

        except Exception as e:
            logger.error(f"Error analyzing project history: {str(e)}")
            return {}

    def _create_empty_analysis(self, token_address: str) -> Dict:
        """Create empty analysis result"""
        return {
            "token_address": token_address,
            "mentions_analysis": {},
            "sentiment_analysis": {},
            "notable_interactions": [],
            "project_history": {},
            "timestamp": datetime.now().isoformat()
        }
