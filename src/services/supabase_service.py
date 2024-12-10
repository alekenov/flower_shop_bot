import os
import logging
from supabase import create_client, Client
from typing import List, Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class SupabaseService:
    def __init__(self):
        """Initialize Supabase client."""
        try:
            self.url = os.getenv("SUPABASE_URL")
            self.key = os.getenv("SUPABASE_KEY")
            if not self.url or not self.key:
                raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
            
            self.client: Client = create_client(self.url, self.key)
            logger.info("Successfully initialized Supabase client")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {str(e)}", exc_info=True)
            raise

    def get_products(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get products from Supabase, optionally filtered by category."""
        try:
            query = self.client.table('products').select('*')
            if category:
                query = query.eq('category', category)
            
            response = query.execute()
            return response.data
        except Exception as e:
            logger.error(f"Failed to get products: {str(e)}", exc_info=True)
            return []

    def get_product_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a product by its name."""
        try:
            response = self.client.table('products') \
                .select('*') \
                .ilike('name', f'%{name}%') \
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Failed to get product by name: {str(e)}", exc_info=True)
            return None

    def save_conversation(self, user_id: int, message: str, response: str) -> None:
        """Save conversation history."""
        try:
            self.client.table('conversations').insert({
                'user_id': user_id,
                'message': message,
                'response': response,
                'created_at': datetime.utcnow().isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Failed to save conversation: {str(e)}", exc_info=True)

    def get_user_preferences(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user preferences."""
        try:
            response = self.client.table('user_preferences') \
                .select('*') \
                .eq('user_id', user_id) \
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Failed to get user preferences: {str(e)}", exc_info=True)
            return None

    def update_user_preferences(self, user_id: int, preferences: Dict[str, Any]) -> None:
        """Update user preferences."""
        try:
            existing = self.get_user_preferences(user_id)
            if existing:
                self.client.table('user_preferences') \
                    .update(preferences) \
                    .eq('user_id', user_id) \
                    .execute()
            else:
                preferences['user_id'] = user_id
                self.client.table('user_preferences') \
                    .insert(preferences) \
                    .execute()
        except Exception as e:
            logger.error(f"Failed to update user preferences: {str(e)}", exc_info=True)

    def save_user_insight(self, user_id: int, insight_type: str, data: Dict[str, Any]) -> None:
        """Save user insight."""
        try:
            self.client.table('user_insights').insert({
                'user_id': user_id,
                'type': insight_type,
                'data': data,
                'created_at': datetime.utcnow().isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Failed to save user insight: {str(e)}", exc_info=True)

    def get_user_insights(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user insights."""
        try:
            response = self.client.table('user_insights') \
                .select('*') \
                .eq('user_id', user_id) \
                .order('created_at', desc=True) \
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Failed to get user insights: {str(e)}", exc_info=True)
            return []

    def save_interaction_pattern(self, user_id: int, pattern_type: str, details: Dict[str, Any]) -> None:
        """Save interaction pattern."""
        try:
            self.client.table('interaction_patterns').insert({
                'user_id': user_id,
                'type': pattern_type,
                'details': details,
                'created_at': datetime.utcnow().isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Failed to save interaction pattern: {str(e)}", exc_info=True)

    def get_conversation_context(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get conversation context."""
        try:
            response = self.client.table('conversation_contexts') \
                .select('*') \
                .eq('user_id', user_id) \
                .order('created_at', desc=True) \
                .limit(1) \
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Failed to get conversation context: {str(e)}", exc_info=True)
            return None

    def update_conversation_context(self, user_id: int, context: Dict[str, Any]) -> None:
        """Update conversation context."""
        try:
            context['user_id'] = user_id
            context['created_at'] = datetime.utcnow().isoformat()
            self.client.table('conversation_contexts') \
                .insert(context) \
                .execute()
        except Exception as e:
            logger.error(f"Failed to update conversation context: {str(e)}", exc_info=True)
