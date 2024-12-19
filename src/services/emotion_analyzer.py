import logging
import re
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class EmotionAnalyzer:
    def __init__(self):
        # Словари для анализа эмоций
        self.emotions = {
            'positive': [
                'спасибо', 'отлично', 'супер', 'круто', 'классно', 'прекрасно',
                'замечательно', 'великолепно', '❤️', '😊', '👍', 'нравится',
                'доволен', 'рад', 'счастлив'
            ],
            'negative': [
                'плохо', 'ужасно', 'отвратительно', 'недоволен', 'разочарован',
                'жаль', 'жалко', 'грустно', '😞', '👎', 'не нравится', 'ненавижу',
                'отстой', 'ужас'
            ],
            'urgent': [
                'срочно', 'быстрее', 'немедленно', 'сейчас', 'скорее', 'спешу',
                'успеть', 'сегодня', 'как можно быстрее', '⚡️'
            ],
            'confused': [
                'не понимаю', 'непонятно', 'как это', 'что это', 'зачем',
                'почему', '🤔', 'странно', 'сложно'
            ]
        }
        
        # Веса для разных типов эмоций
        self.weights = {
            'positive': 1.0,
            'negative': 1.2,  # Негативным эмоциям придаем больший вес
            'urgent': 1.5,    # Срочность имеет высокий приоритет
            'confused': 0.8
        }
        
        # Паттерны для определения интенсивности
        self.intensity_patterns = {
            'high': [
                r'очень\s+\w+', r'крайне\s+\w+', r'сильно\s+\w+',
                r'!!!+', r'ОЧЕНЬ', r'!!', r'СРОЧНО'
            ],
            'low': [
                r'немного\s+\w+', r'слегка\s+\w+', r'чуть\s+\w+',
                r'возможно', r'наверное', r'может быть'
            ]
        }

    def _preprocess_text(self, text: str) -> str:
        """Предобработка текста для анализа."""
        # Приводим к нижнему регистру
        text = text.lower()
        # Удаляем лишние пробелы
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _check_intensity(self, text: str) -> float:
        """Определяет интенсивность эмоций в тексте."""
        intensity = 1.0
        
        # Проверяем паттерны высокой интенсивности
        for pattern in self.intensity_patterns['high']:
            if re.search(pattern, text, re.IGNORECASE):
                intensity *= 1.5
                
        # Проверяем паттерны низкой интенсивности
        for pattern in self.intensity_patterns['low']:
            if re.search(pattern, text, re.IGNORECASE):
                intensity *= 0.7
                
        return min(intensity, 2.0)  # Ограничиваем максимальную интенсивность

    def _calculate_emotion_scores(self, text: str) -> Dict[str, float]:
        """Вычисляет оценки для каждой эмоции."""
        scores = {emotion: 0.0 for emotion in self.emotions.keys()}
        words = set(text.split())
        
        for emotion, keywords in self.emotions.items():
            for keyword in keywords:
                if keyword in text:
                    scores[emotion] += self.weights[emotion]
                    
        # Применяем интенсивность
        intensity = self._check_intensity(text)
        for emotion in scores:
            scores[emotion] *= intensity
            
        return scores

    def _get_dominant_emotions(self, scores: Dict[str, float], threshold: float = 0.5) -> List[str]:
        """Определяет доминирующие эмоции."""
        max_score = max(scores.values()) if scores else 0
        if max_score == 0:
            return []
            
        return [
            emotion for emotion, score in scores.items()
            if score >= max_score * threshold
        ]

    async def analyze(self, text: str) -> Dict[str, any]:
        """
        Анализирует эмоциональную составляющую текста.
        Возвращает словарь с оценками эмоций и рекомендациями.
        """
        try:
            processed_text = self._preprocess_text(text)
            scores = self._calculate_emotion_scores(processed_text)
            dominant_emotions = self._get_dominant_emotions(scores)
            
            response = {
                'emotion_scores': scores,
                'dominant_emotions': dominant_emotions,
                'intensity': self._check_intensity(processed_text),
                'recommendations': self._get_recommendations(dominant_emotions, scores)
            }
            
            logger.info(f"Emotion analysis results: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Error in emotion analysis: {str(e)}")
            return {
                'emotion_scores': {},
                'dominant_emotions': [],
                'intensity': 1.0,
                'recommendations': []
            }

    def _get_recommendations(self, dominant_emotions: List[str], scores: Dict[str, float]) -> List[str]:
        """Генерирует рекомендации на основе эмоционального анализа."""
        recommendations = []
        
        if 'negative' in dominant_emotions:
            recommendations.append('Проявить особое внимание и эмпатию')
            recommendations.append('Предложить альтернативные варианты')
            
        if 'urgent' in dominant_emotions:
            recommendations.append('Ускорить обработку запроса')
            recommendations.append('Предложить экспресс-варианты')
            
        if 'confused' in dominant_emotions:
            recommendations.append('Дать более подробное объяснение')
            recommendations.append('Использовать простые формулировки')
            
        if 'positive' in dominant_emotions:
            recommendations.append('Поддержать позитивный настрой')
            recommendations.append('Предложить дополнительные опции')
            
        if not dominant_emotions:
            recommendations.append('Использовать нейтральный тон')
            
        return recommendations
