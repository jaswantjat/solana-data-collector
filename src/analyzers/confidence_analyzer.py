from discord_webhook import DiscordWebhook, DiscordEmbed
from datetime import datetime
import json
from src.config import DISCORD_WEBHOOK_URL

class ConfidenceAnalyzer:
    def __init__(self):
        self.weights = self.load_weights()
        self.threshold = 70  # Minimum confidence score to trigger notification

    def load_weights(self):
        """
        Load scoring weights from configuration
        """
        try:
            with open('config/scoring_weights.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Default weights if configuration file doesn't exist
            return {
                'deployer': {
                    'previous_tokens': 0.15,
                    'success_rate': 0.10,
                    'selling_pattern': 0.10
                },
                'holders': {
                    'distribution': 0.10,
                    'top_holder_performance': 0.15,
                    'sniper_activity': -0.05
                },
                'social': {
                    'notable_mentions': 0.10,
                    'sentiment': 0.05,
                    'account_age': 0.05
                },
                'trading': {
                    'volume': 0.10,
                    'liquidity': 0.10
                }
            }

    def calculate_deployer_score(self, deployer_data):
        """
        Calculate confidence score based on deployer metrics
        """
        score = 0
        weights = self.weights['deployer']
        
        # Previous tokens score
        if deployer_data.get('total_tokens', 0) > 0:
            success_rate = deployer_data.get('successful_tokens', 0) / deployer_data['total_tokens']
            score += weights['success_rate'] * (success_rate * 100)
        
        # Selling pattern score
        if deployer_data.get('total_sales', 0) == 0:
            score += weights['selling_pattern'] * 100  # Full score if no sales
        else:
            # Penalize based on sale timing and size
            sale_penalty = min(100, (deployer_data.get('total_amount_sold', 0) / 1000000) * 100)
            score += weights['selling_pattern'] * (100 - sale_penalty)

        return score

    def calculate_holder_score(self, holder_data, performance_data):
        """
        Calculate confidence score based on holder metrics
        """
        score = 0
        weights = self.weights['holders']
        
        # Holder distribution score
        total_holders = holder_data.get('total_holders', 0)
        if total_holders > 1000:
            score += weights['distribution'] * 100
        else:
            score += weights['distribution'] * (total_holders / 1000 * 100)
        
        # Top holder performance score
        if performance_data:
            avg_win_rate = sum(h['win_rate'] for h in performance_data) / len(performance_data)
            score += weights['top_holder_performance'] * (avg_win_rate * 100)
        
        # Sniper activity penalty
        sniper_count = holder_data.get('sniper_count', 0)
        if sniper_count > 0:
            penalty = min(100, sniper_count * 10)
            score += weights['sniper_activity'] * penalty

        return score

    def calculate_social_score(self, twitter_data):
        """
        Calculate confidence score based on social metrics
        """
        score = 0
        weights = self.weights['social']
        
        # Notable mentions score
        notable_mentions = len(twitter_data.get('notable_mentions', []))
        if notable_mentions > 0:
            score += weights['notable_mentions'] * min(100, notable_mentions * 20)
        
        # Sentiment score
        sentiment = twitter_data.get('sentiment_score', 0)
        score += weights['sentiment'] * ((sentiment + 1) * 50)  # Convert -1 to 1 range to 0-100
        
        # Account age score
        if twitter_data.get('account_history'):
            account_age_days = (datetime.utcnow() - twitter_data['account_history']['created_at']).days
            score += weights['account_age'] * min(100, account_age_days / 30 * 100)

        return score

    def calculate_trading_score(self, trading_data):
        """
        Calculate confidence score based on trading metrics
        """
        score = 0
        weights = self.weights['trading']
        
        # Volume score
        daily_volume = trading_data.get('volume_24h', 0)
        if daily_volume > 100000:  # $100k daily volume
            score += weights['volume'] * 100
        else:
            score += weights['volume'] * (daily_volume / 100000 * 100)
        
        # Liquidity score
        liquidity = trading_data.get('liquidity', 0)
        if liquidity > 50000:  # $50k liquidity
            score += weights['liquidity'] * 100
        else:
            score += weights['liquidity'] * (liquidity / 50000 * 100)

        return score

    def calculate_confidence_score(self, token_data):
        """
        Calculate overall confidence score based on all metrics
        """
        score = 0
        
        # Calculate individual component scores
        deployer_score = self.calculate_deployer_score(token_data.get('deployer_data', {}))
        holder_score = self.calculate_holder_score(
            token_data.get('holder_data', {}),
            token_data.get('holder_performance', [])
        )
        social_score = self.calculate_social_score(token_data.get('twitter_data', {}))
        trading_score = self.calculate_trading_score(token_data.get('trading_data', {}))
        
        # Combine scores
        score = deployer_score + holder_score + social_score + trading_score
        
        return min(100, max(0, score))  # Ensure score is between 0 and 100

    def format_analysis_summary(self, token_address, token_data, confidence_score):
        """
        Format analysis summary for Discord notification
        """
        deployer_data = token_data.get('deployer_data', {})
        holder_data = token_data.get('holder_data', {})
        twitter_data = token_data.get('twitter_data', {})
        trading_data = token_data.get('trading_data', {})

        summary = []
        summary.append(f"🔍 Token Analysis Report: {token_address}")
        summary.append(f"Confidence Score: {confidence_score:.1f}/100")
        
        summary.append("\n🏗️ Deployer Analysis:")
        summary.append(f"- Previous Successful Tokens: {deployer_data.get('successful_tokens', 0)}")
        summary.append(f"- Total Sales: {deployer_data.get('total_sales', 0)}")
        
        summary.append("\n👥 Holder Analysis:")
        summary.append(f"- Total Holders: {holder_data.get('total_holders', 0)}")
        summary.append(f"- Sniper Wallets: {holder_data.get('sniper_count', 0)}")
        
        summary.append("\n🐦 Social Analysis:")
        summary.append(f"- Notable Mentions: {len(twitter_data.get('notable_mentions', []))}")
        summary.append(f"- Sentiment: {twitter_data.get('sentiment_score', 0):.2f}")
        
        summary.append("\n📊 Trading Analysis:")
        summary.append(f"- 24h Volume: ${trading_data.get('volume_24h', 0):,.2f}")
        summary.append(f"- Liquidity: ${trading_data.get('liquidity', 0):,.2f}")

        return "\n".join(summary)

    async def send_discord_notification(self, token_address, token_data, confidence_score):
        """
        Send analysis results to Discord if confidence score meets threshold
        """
        if confidence_score < self.threshold:
            return False

        try:
            webhook = DiscordWebhook(
                url=DISCORD_WEBHOOK_URL,
                username="Token Analyzer Bot"
            )

            # Create embed
            embed = DiscordEmbed(
                title=f"🚀 High Confidence Token Detected!",
                description=self.format_analysis_summary(token_address, token_data, confidence_score),
                color=0x00ff00
            )

            embed.set_footer(text=f"Analysis Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            webhook.add_embed(embed)
            
            response = webhook.execute()
            return response.status_code == 200

        except Exception as e:
            print(f"Error sending Discord notification: {str(e)}")
            return False
