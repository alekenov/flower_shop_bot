import logging
from datetime import datetime, date
from typing import Dict, Optional, List
from uuid import UUID
import json
from dataclasses import dataclass

from src.services.supabase_service import supabase_service
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
        self.config = Config()
        
    async def log_token_usage(self, usage: TokenUsage) -> None:
        """Логирует использование токенов."""
        try:
            await supabase_service.execute_query(
                """
                INSERT INTO token_usage (
                    prompt_tokens, completion_tokens, total_tokens,
                    cost_usd, scenario, message_id, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    usage.prompt_tokens,
                    usage.completion_tokens,
                    usage.total_tokens,
                    usage.cost_usd,
                    usage.scenario,
                    usage.message_id,
                    datetime.now()
                )
            )
            logger.info(f"Token usage logged for message {usage.message_id}")
        except Exception as e:
            logger.error(f"Failed to log token usage: {str(e)}")

    async def log_response_quality(self, quality: ResponseQuality) -> None:
        """Логирует качество ответа."""
        try:
            await supabase_service.execute_query(
                """
                INSERT INTO response_quality (
                    message_id, scenario, response_relevance,
                    format_compliance, emotional_match, flags,
                    user_rating, completed_order, processing_time_ms,
                    created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    quality.message_id,
                    quality.scenario,
                    quality.response_relevance,
                    quality.format_compliance,
                    quality.emotional_match,
                    json.dumps(quality.flags),
                    quality.user_rating,
                    quality.completed_order,
                    quality.processing_time_ms,
                    datetime.now()
                )
            )
            logger.info(f"Response quality logged for message {quality.message_id}")
        except Exception as e:
            logger.error(f"Failed to log response quality: {str(e)}")

    async def get_daily_token_usage(self, day: date) -> Dict[str, int]:
        """Получает статистику использования токенов за день."""
        try:
            results = await supabase_service.execute_query(
                """
                SELECT 
                    SUM(prompt_tokens) as prompt_tokens,
                    SUM(completion_tokens) as completion_tokens,
                    SUM(total_tokens) as total_tokens,
                    SUM(cost_usd) as total_cost
                FROM token_usage
                WHERE DATE(created_at) = %s
                """,
                (day,)
            )
            
            if results:
                return {
                    'prompt_tokens': results[0]['prompt_tokens'] or 0,
                    'completion_tokens': results[0]['completion_tokens'] or 0,
                    'total_tokens': results[0]['total_tokens'] or 0,
                    'total_cost': float(results[0]['total_cost'] or 0)
                }
            return {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0, 'total_cost': 0.0}
            
        except Exception as e:
            logger.error(f"Failed to get daily token usage: {str(e)}")
            return {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0, 'total_cost': 0.0}

    async def get_scenario_performance(self, scenario: str, days: int = 7) -> Dict[str, float]:
        """Получает статистику производительности сценария."""
        try:
            results = await supabase_service.execute_query(
                """
                SELECT 
                    AVG(response_relevance) as avg_relevance,
                    AVG(format_compliance) as avg_compliance,
                    AVG(emotional_match) as avg_emotional,
                    AVG(CASE WHEN user_rating IS NOT NULL THEN user_rating ELSE 0 END) as avg_rating,
                    COUNT(CASE WHEN completed_order THEN 1 END)::float / 
                        NULLIF(COUNT(*), 0) as completion_rate
                FROM response_quality
                WHERE scenario = %s
                AND created_at >= CURRENT_DATE - INTERVAL '%s days'
                """,
                (scenario, days)
            )
            
            if results:
                return {
                    'avg_relevance': float(results[0]['avg_relevance'] or 0),
                    'avg_compliance': float(results[0]['avg_compliance'] or 0),
                    'avg_emotional': float(results[0]['avg_emotional'] or 0),
                    'avg_rating': float(results[0]['avg_rating'] or 0),
                    'completion_rate': float(results[0]['completion_rate'] or 0)
                }
            return {
                'avg_relevance': 0.0,
                'avg_compliance': 0.0,
                'avg_emotional': 0.0,
                'avg_rating': 0.0,
                'completion_rate': 0.0
            }
            
        except Exception as e:
            logger.error(f"Failed to get scenario performance: {str(e)}")
            return {
                'avg_relevance': 0.0,
                'avg_compliance': 0.0,
                'avg_emotional': 0.0,
                'avg_rating': 0.0,
                'completion_rate': 0.0
            }

# Create a global instance
monitoring_service = MonitoringService()
