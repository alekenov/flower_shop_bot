import logging
from datetime import datetime, date, timedelta
from typing import Dict, Optional, List
from uuid import UUID
import json
from dataclasses import dataclass
from google.cloud import monitoring_v3
import time

from services.supabase_service import supabase_service
from services.config_service import config_service

logger = logging.getLogger(__name__)

@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    scenario: str
    message_id: Optional[str]

@dataclass
class ResponseQuality:
    message_id: Optional[str]
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
        self.config = config_service
        self.project_id = self.config.get_config('project_id', service_name='google')
        if self.project_id:
            self.client = monitoring_v3.MetricServiceClient()
            self.project_name = f"projects/{self.project_id}"
        
    def record_metric(self, metric_type: str, value: float, labels: Dict[str, str] = None):
        """Записывает метрику в Cloud Monitoring."""
        try:
            if not self.project_id:
                return

            series = monitoring_v3.TimeSeries()
            series.metric.type = f"custom.googleapis.com/flower_shop_bot/{metric_type}"
            
            if labels:
                series.metric.labels.update(labels)
            
            series.resource.type = "global"
            point = series.points.add()
            point.value.double_value = value
            now = time.time()
            point.interval.end_time.seconds = int(now)
            
            self.client.create_time_series(
                request={
                    "name": self.project_name,
                    "time_series": [series]
                }
            )
            logger.debug(f"Recorded metric {metric_type}: {value}")
        except Exception as e:
            logger.error(f"Failed to record metric: {e}")
        
    async def log_token_usage(self, usage: TokenUsage) -> None:
        """Логирует использование токенов."""
        try:
            current_time = datetime.now().isoformat()
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
                    current_time  
                )
            )
            # Записываем метрики
            self.record_metric("token_usage_total", usage.total_tokens, {"scenario": usage.scenario})
            self.record_metric("token_cost_usd", usage.cost_usd, {"scenario": usage.scenario})
            
            logger.info(f"Token usage logged for message {usage.message_id}")
        except Exception as e:
            logger.error(f"Failed to log token usage: {e}")

    async def log_response_quality(self, quality: ResponseQuality) -> None:
        """Логирует качество ответа."""
        try:
            current_time = datetime.now().isoformat()
            flags_json = json.dumps(quality.flags, ensure_ascii=False)
            
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
                    flags_json,
                    quality.user_rating,
                    quality.completed_order,
                    quality.processing_time_ms,
                    current_time  
                )
            )
            # Записываем метрики
            self.record_metric("response_quality", quality.response_relevance, {"scenario": quality.scenario})
            if quality.processing_time_ms:
                self.record_metric("processing_time_ms", quality.processing_time_ms, {"scenario": quality.scenario})
            if quality.user_rating:
                self.record_metric("user_rating", quality.user_rating, {"scenario": quality.scenario})
                
            logger.info(f"Response quality logged for message {quality.message_id}")
        except Exception as e:
            logger.error(f"Failed to log response quality: {e}")

    async def get_daily_token_usage(self, day: date) -> Dict[str, int]:
        """Получает статистику использования токенов за день."""
        try:
            day_str = day.isoformat()
            result = await supabase_service.execute_query(
                """
                SELECT 
                    SUM(prompt_tokens) as prompt_tokens,
                    SUM(completion_tokens) as completion_tokens,
                    SUM(total_tokens) as total_tokens,
                    SUM(cost_usd) as total_cost
                FROM token_usage
                WHERE DATE(created_at) = %s
                """,
                (day_str,)
            )
            
            if not result or not result[0]:
                return {
                    'prompt_tokens': 0,
                    'completion_tokens': 0,
                    'total_tokens': 0,
                    'total_cost': 0.0
                }
                
            row = result[0]
            return {
                'prompt_tokens': row[0] or 0,
                'completion_tokens': row[1] or 0,
                'total_tokens': row[2] or 0,
                'total_cost': float(row[3] or 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get daily token usage: {e}")
            return {
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0,
                'total_cost': 0.0
            }

    async def get_scenario_performance(self, scenario: str, days: int = 7) -> Dict[str, float]:
        """Получает статистику производительности сценария."""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            result = await supabase_service.execute_query(
                """
                SELECT 
                    AVG(response_relevance) as avg_relevance,
                    AVG(format_compliance) as avg_compliance,
                    AVG(emotional_match) as avg_emotional,
                    AVG(CASE WHEN user_rating IS NOT NULL THEN user_rating ELSE NULL END) as avg_rating,
                    COUNT(CASE WHEN completed_order = true THEN 1 END)::float / 
                        NULLIF(COUNT(CASE WHEN completed_order IS NOT NULL THEN 1 END), 0) as completion_rate,
                    AVG(processing_time_ms) as avg_processing_time
                FROM response_quality
                WHERE scenario = %s
                AND created_at >= %s
                """,
                (scenario, cutoff_date)
            )
            
            if not result or not result[0]:
                return {
                    'avg_relevance': 0.0,
                    'avg_compliance': 0.0,
                    'avg_emotional': 0.0,
                    'avg_rating': 0.0,
                    'completion_rate': 0.0,
                    'avg_processing_time': 0.0
                }
                
            row = result[0]
            return {
                'avg_relevance': float(row[0] or 0),
                'avg_compliance': float(row[1] or 0),
                'avg_emotional': float(row[2] or 0),
                'avg_rating': float(row[3] or 0),
                'completion_rate': float(row[4] or 0),
                'avg_processing_time': float(row[5] or 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get scenario performance: {e}")
            return {
                'avg_relevance': 0.0,
                'avg_compliance': 0.0,
                'avg_emotional': 0.0,
                'avg_rating': 0.0,
                'completion_rate': 0.0,
                'avg_processing_time': 0.0
            }

# Create a global instance
monitoring_service = MonitoringService()
