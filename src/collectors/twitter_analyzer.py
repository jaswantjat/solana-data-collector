import tweepy
from textblob import TextBlob
import json
import asyncio
from datetime import datetime, timedelta
from ..config import (
    TWITTER_API_KEY,
    TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_SECRET,
    TWITTER_BEARER_TOKEN
)

class TwitterAnalyzer:
    def __init__(self):
        # Initialize Twitter API v2 client
        self.client = tweepy.Client(
            bearer_token=TWITTER_BEARER_TOKEN,
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_SECRET,
            wait_on_rate_limit=True
        )
        self.notable_accounts = self.load_notable_accounts()

    def load_notable_accounts(self):
        """
        Load list of notable Twitter accounts
        """
        try:
            with open('data/notable_accounts.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                'influencers': [],
                'projects': [],
                'traders': []
            }

    async def search_token_mentions(self, token_address, days_back=7):
        """
        Search for tweets mentioning the token address
        """
        query = f"{token_address} -is:retweet"
        start_time = datetime.utcnow() - timedelta(days=days_back)

        try:
            tweets = self.client.search_recent_tweets(
                query=query,
                start_time=start_time,
                max_results=100,
                tweet_fields=['created_at', 'public_metrics', 'author_id'],
                user_fields=['username', 'public_metrics', 'description'],
                expansions=['author_id']
            )

            if not tweets.data:
                return {
                    'total_mentions': 0,
                    'sentiment_score': 0,
                    'notable_mentions': [],
                    'tweets': []
                }

            # Process tweets and calculate sentiment
            processed_tweets = []
            total_sentiment = 0
            notable_mentions = []

            users = {user.id: user for user in tweets.includes['users']} if tweets.includes else {}

            for tweet in tweets.data:
                # Get tweet author
                author = users.get(tweet.author_id)
                if not author:
                    continue

                # Calculate sentiment
                sentiment = TextBlob(tweet.text).sentiment.polarity

                # Check if author is notable
                is_notable = self.is_notable_account(author)

                tweet_data = {
                    'id': tweet.id,
                    'text': tweet.text,
                    'created_at': tweet.created_at,
                    'author': author.username,
                    'author_followers': author.public_metrics['followers_count'],
                    'likes': tweet.public_metrics['like_count'],
                    'retweets': tweet.public_metrics['retweet_count'],
                    'sentiment': sentiment
                }

                if is_notable:
                    notable_mentions.append(tweet_data)

                processed_tweets.append(tweet_data)
                total_sentiment += sentiment

            avg_sentiment = total_sentiment / len(processed_tweets) if processed_tweets else 0

            return {
                'total_mentions': len(processed_tweets),
                'sentiment_score': avg_sentiment,
                'notable_mentions': notable_mentions,
                'tweets': processed_tweets
            }

        except Exception as e:
            print(f"Error searching tweets: {str(e)}")
            return {
                'total_mentions': 0,
                'sentiment_score': 0,
                'notable_mentions': [],
                'tweets': []
            }

    def is_notable_account(self, user):
        """
        Check if a Twitter user is considered notable based on our criteria
        """
        # Check against our list of known notable accounts
        for category in ['influencers', 'projects', 'traders']:
            if any(acc['username'].lower() == user.username.lower() 
                  for acc in self.notable_accounts[category]):
                return True

        # Check follower count threshold
        if user.public_metrics['followers_count'] >= 50000:  # Configurable threshold
            return True

        return False

    async def check_account_history(self, username):
        """
        Check account name history and profile changes
        Note: Twitter API v2 doesn't provide direct access to username history,
        so we'll track what we can about the account
        """
        try:
            user = self.client.get_user(
                username=username,
                user_fields=['created_at', 'description', 'public_metrics']
            )

            if not user.data:
                return None

            # Get recent tweets to analyze patterns
            tweets = self.client.get_users_tweets(
                user.data.id,
                max_results=100,
                tweet_fields=['created_at']
            )

            tweet_history = []
            if tweets.data:
                for tweet in tweets.data:
                    tweet_history.append({
                        'created_at': tweet.created_at,
                        'text': tweet.text
                    })

            return {
                'username': username,
                'created_at': user.data.created_at,
                'followers': user.data.public_metrics['followers_count'],
                'following': user.data.public_metrics['following_count'],
                'tweet_count': user.data.public_metrics['tweet_count'],
                'description': user.data.description,
                'recent_tweets': tweet_history
            }

        except Exception as e:
            print(f"Error checking account history: {str(e)}")
            return None

    def format_analysis_results(self, token_address, mention_data, account_history=None):
        """
        Format the Twitter analysis results for better readability
        """
        output = []
        output.append(f"\nTwitter Analysis Report for {token_address}")
        output.append("-" * 50)

        # Mention Statistics
        output.append(f"\nMention Statistics:")
        output.append(f"Total Mentions: {mention_data['total_mentions']}")
        output.append(f"Overall Sentiment: {mention_data['sentiment_score']:.2f} "
                     f"({'Positive' if mention_data['sentiment_score'] > 0 else 'Negative' if mention_data['sentiment_score'] < 0 else 'Neutral'})")

        # Notable Mentions
        if mention_data['notable_mentions']:
            output.append("\nNotable Mentions:")
            for mention in mention_data['notable_mentions']:
                output.append(f"\n- @{mention['author']} ({mention['author_followers']:,} followers)")
                output.append(f"  Tweet: {mention['text'][:100]}...")
                output.append(f"  Engagement: {mention['likes']} likes, {mention['retweets']} retweets")
                output.append(f"  Sentiment: {mention['sentiment']:.2f}")

        # Account History (if available)
        if account_history:
            output.append("\nOfficial Account Analysis:")
            output.append(f"Account Age: {(datetime.utcnow() - account_history['created_at']).days} days")
            output.append(f"Followers: {account_history['followers']:,}")
            output.append(f"Following: {account_history['following']:,}")
            output.append(f"Total Tweets: {account_history['tweet_count']:,}")

        return "\n".join(output)
