import logging
from datetime import datetime, date
from typing import Dict, Optional, List
from uuid import UUID
import json
from dataclasses import dataclass

from src.database.database import Database
from src.config.config import Config

logger = logging.getLogger(__name__)

@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    scenario: str
    message_id: UUID

@dataclass
class ResponseQuality:
    message_id: UUID
    scenario: str
    response_relevance: float
    format_compliance: float
    emotional_match: float
    flags: Dict[str, bool]
    user_rating: Optional[int] = None
    completed_order: Optional[bool] = None
    processing_time_ms: Optional[int] = None

class MonitoringService:
    def __init__(self):
        self.db = Database()
        self.config = Config()
        
    async def log_token_usage(self, usage: TokenUsage):
        """Логирует использование токенов."""
        query = """
            INSERT INTO token_usage (
                prompt_tokens, completion_tokens, total_tokens,
                cost_usd, scenario, message_id
            ) VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
        """
        try:
            await self.db.execute(
                query,
                usage.prompt_tokens,
                usage.completion_tokens,
                usage.total_tokens,
                usage.cost_usd,
                usage.scenario,
                usage.message_id
            )
            logger.info(f"Logged token usage: {usage.total_tokens} tokens for {usage.scenario}")
        except Exception as e:
            logger.error(f"Error logging token usage: {str(e)}")
            
    async def log_response_quality(self, quality: ResponseQuality):
        """Логирует качество ответа."""
        query = """
            INSERT INTO response_quality (
                message_id, scenario, response_relevance,
                format_compliance, emotional_match,
                missing_price, incorrect_format, inappropriate_tone,
                user_rating, completed_order, processing_time_ms
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING id
        """
        try:
            await self.db.execute(
                query,
                quality.message_id,
                quality.scenario,
                quality.response_relevance,
                quality.format_compliance,
                quality.emotional_match,
                quality.flags.get('missing_price', False),
                quality.flags.get('incorrect_format', False),
                quality.flags.get('inappropriate_tone', False),
                quality.user_rating,
                quality.completed_order,
                quality.processing_time_ms
            )
            logger.info(f"Logged response quality for message {quality.message_id}")
        except Exception as e:
            logger.error(f"Error logging response quality: {str(e)}")
            
    async def get_daily_stats(self, day: date) -> Dict:
        """Получает статистику за день."""
        query = """
            SELECT * FROM daily_stats
            WHERE date = $1
        """
        try:
            stats = await self.db.fetchrow(query, day)
            return dict(stats) if stats else {}
        except Exception as e:
            logger.error(f"Error getting daily stats: {str(e)}")
            return {}
            
    async def get_token_usage_report(self, start_date: date, end_date: date) -> Dict:
        """Получает отчет по использованию токенов за период."""
        query = """
            SELECT 
                DATE(timestamp) as day,
                COUNT(*) as requests,
                SUM(total_tokens) as total_tokens,
                SUM(cost_usd) as total_cost,
                AVG(total_tokens) as avg_tokens_per_request,
                scenario,
                COUNT(*) FILTER (WHERE total_tokens > 1000) as expensive_requests
            FROM token_usage
            WHERE timestamp::date BETWEEN $1 AND $2
            GROUP BY DATE(timestamp), scenario
            ORDER BY day DESC, scenario
        """
        try:
            rows = await self.db.fetch(query, start_date, end_date)
            return self._format_token_report(rows)
        except Exception as e:
            logger.error(f"Error getting token usage report: {str(e)}")
            return {}
            
    async def get_quality_report(self, start_date: date, end_date: date) -> Dict:
        """Получает отчет по качеству ответов за период."""
        query = """
            SELECT 
                DATE(timestamp) as day,
                scenario,
                AVG(response_relevance) as avg_relevance,
                AVG(format_compliance) as avg_format,
                AVG(emotional_match) as avg_emotional,
                COUNT(*) FILTER (WHERE user_rating >= 4) as good_ratings,
                COUNT(*) FILTER (WHERE user_rating < 3) as bad_ratings,
                COUNT(*) FILTER (WHERE completed_order) as completed_orders
            FROM response_quality
            WHERE timestamp::date BETWEEN $1 AND $2
            GROUP BY DATE(timestamp), scenario
            ORDER BY day DESC, scenario
        """
        try:
            rows = await self.db.fetch(query, start_date, end_date)
            return self._format_quality_report(rows)
        except Exception as e:
            logger.error(f"Error getting quality report: {str(e)}")
            return {}
    
    def _format_token_report(self, rows: List[Dict]) -> Dict:
        """Форматирует отчет по токенам."""
        report = {}
        for row in rows:
            day = row['day'].isoformat()
            if day not in report:
                report[day] = {
                    'total_requests': 0,
                    'total_tokens': 0,
                    'total_cost': 0,
                    'by_scenario': {}
                }
            
            scenario = row['scenario']
            report[day]['total_requests'] += row['requests']
            report[day]['total_tokens'] += row['total_tokens']
            report[day]['total_cost'] += float(row['total_cost'])
            report[day]['by_scenario'][scenario] = {
                'requests': row['requests'],
                'tokens': row['total_tokens'],
                'avg_tokens': round(row['avg_tokens_per_request'], 2),
                'expensive_requests': row['expensive_requests']
            }
        return report
    
    def _format_quality_report(self, rows: List[Dict]) -> Dict:
        """Форматирует отчет по качеству."""
        report = {}
        for row in rows:
            day = row['day'].isoformat()
            if day not in report:
                report[day] = {
                    'overall_quality': 0,
                    'by_scenario': {}
                }
            
            scenario = row['scenario']
            quality_score = (
                float(row['avg_relevance']) * 0.4 +
                float(row['avg_format']) * 0.3 +
                float(row['avg_emotional']) * 0.3
            )
            
            report[day]['by_scenario'][scenario] = {
                'quality_score': round(quality_score, 2),
                'good_ratings': row['good_ratings'],
                'bad_ratings': row['bad_ratings'],
                'completed_orders': row['completed_orders']
            }
            
            # Обновляем общий показатель качества
            scenarios = len(report[day]['by_scenario'])
            report[day]['overall_quality'] = round(
                (report[day]['overall_quality'] * (scenarios - 1) + quality_score) / scenarios,
                2
            )
        return report
