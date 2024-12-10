import { SupabaseClient } from 'https://esm.sh/@supabase/supabase-js@2.39.0';

interface CacheEntry {
  id?: number;
  query_hash: string;
  query_text: string;
  response_text: string;
  created_at?: string;
  updated_at?: string;
  hit_count?: number;
}

export class ResponseCache {
  private supabase: SupabaseClient;
  private tableName: string = 'ai_response_cache';
  private ttlHours: number = 24; // Время жизни кэша в часах

  constructor(supabase: SupabaseClient) {
    this.supabase = supabase;
  }

  // Создает хэш из текста запроса
  private createHash(text: string): string {
    // Нормализуем текст: приводим к нижнему регистру и убираем лишние пробелы
    const normalizedText = text.toLowerCase().trim().replace(/\s+/g, ' ');
    
    // Используем простой хэш для демонстрации
    // В продакшене лучше использовать более надежный алгоритм
    let hash = 0;
    for (let i = 0; i < normalizedText.length; i++) {
      const char = normalizedText.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return hash.toString(16);
  }

  // Проверяет, не устарела ли запись
  private isEntryValid(entry: CacheEntry): boolean {
    if (!entry.created_at) return false;
    
    const createdAt = new Date(entry.created_at);
    const now = new Date();
    const hoursDiff = (now.getTime() - createdAt.getTime()) / (1000 * 60 * 60);
    
    return hoursDiff < this.ttlHours;
  }

  // Получает ответ из кэша
  async get(queryText: string): Promise<string | null> {
    try {
      const queryHash = this.createHash(queryText);
      
      const { data: entries, error } = await this.supabase
        .from(this.tableName)
        .select('*')
        .eq('query_hash', queryHash)
        .limit(1);
      
      if (error) throw error;
      
      if (!entries || entries.length === 0) return null;
      
      const entry = entries[0];
      
      // Проверяем валидность записи
      if (!this.isEntryValid(entry)) {
        // Удаляем устаревшую запись
        await this.supabase
          .from(this.tableName)
          .delete()
          .eq('id', entry.id);
        return null;
      }
      
      // Увеличиваем счетчик использования
      await this.supabase
        .from(this.tableName)
        .update({ 
          hit_count: (entry.hit_count || 0) + 1,
          updated_at: new Date().toISOString()
        })
        .eq('id', entry.id);
      
      return entry.response_text;
    } catch (error) {
      console.error('Error getting cache entry:', error);
      return null;
    }
  }

  // Сохраняет ответ в кэш
  async set(queryText: string, responseText: string): Promise<void> {
    try {
      const queryHash = this.createHash(queryText);
      
      // Проверяем существование записи
      const { data: existing } = await this.supabase
        .from(this.tableName)
        .select('id')
        .eq('query_hash', queryHash)
        .limit(1);
      
      if (existing && existing.length > 0) {
        // Обновляем существующую запись
        await this.supabase
          .from(this.tableName)
          .update({
            response_text: responseText,
            updated_at: new Date().toISOString(),
            hit_count: 1
          })
          .eq('id', existing[0].id);
      } else {
        // Создаем новую запись
        await this.supabase
          .from(this.tableName)
          .insert({
            query_hash: queryHash,
            query_text: queryText,
            response_text: responseText,
            hit_count: 1
          });
      }
    } catch (error) {
      console.error('Error setting cache entry:', error);
    }
  }

  // Очищает устаревшие записи
  async cleanup(): Promise<void> {
    try {
      const expirationDate = new Date();
      expirationDate.setHours(expirationDate.getHours() - this.ttlHours);
      
      await this.supabase
        .from(this.tableName)
        .delete()
        .lt('created_at', expirationDate.toISOString());
    } catch (error) {
      console.error('Error cleaning up cache:', error);
    }
  }
}
