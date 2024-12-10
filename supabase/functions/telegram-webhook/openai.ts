import { ResponseCache } from './cache.ts';
import { SupabaseClient } from 'https://esm.sh/@supabase/supabase-js@2.39.0';

interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export class OpenAIClient {
  private apiKey: string;
  private model: string;
  private baseUrl: string;
  private cache: ResponseCache;

  constructor(apiKey: string, supabase: SupabaseClient, model = 'gpt-3.5-turbo') {
    this.apiKey = apiKey;
    this.model = model;
    this.baseUrl = 'https://api.openai.com/v1';
    this.cache = new ResponseCache(supabase);
  }

  async chat(messages: ChatMessage[]): Promise<string> {
    try {
      const response = await fetch(`${this.baseUrl}/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.apiKey}`,
        },
        body: JSON.stringify({
          model: this.model,
          messages,
          temperature: 0.7,
          max_tokens: 500,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(`OpenAI API error: ${JSON.stringify(error)}`);
      }

      const data = await response.json();
      return data.choices[0].message.content.trim();
    } catch (error) {
      console.error('Error calling OpenAI:', error);
      throw error;
    }
  }

  // Подготовка контекста для цветочного магазина
  private getBaseContext(): ChatMessage[] {
    return [
      {
        role: 'system',
        content: `Вы - помощник цветочного магазина. Ваша задача - помочь клиентам выбрать цветы и оформить заказ.
        
        Правила общения:
        1. Всегда будьте вежливы и дружелюбны
        2. Давайте конкретные рекомендации по выбору цветов
        3. Если клиент спрашивает о цене или наличии, предложите использовать команду /products
        4. При вопросах о доставке, укажите что доставка возможна по городу
        5. Если клиент готов сделать заказ, попросите использовать команду /order
        
        Ограничения:
        1. Не называйте конкретные цены, так как они могут меняться
        2. Не принимайте заказы напрямую, только через команду /order
        3. Не давайте обещаний по времени доставки`
      }
    ];
  }

  // Обработка сообщения пользователя с использованием кэша
  async processUserMessage(userMessage: string): Promise<string> {
    try {
      // Проверяем кэш
      const cachedResponse = await this.cache.get(userMessage);
      if (cachedResponse) {
        console.log('Cache hit for message:', userMessage);
        return cachedResponse;
      }

      // Если ответа нет в кэше, получаем его от OpenAI
      console.log('Cache miss for message:', userMessage);
      const context = this.getBaseContext();
      context.push({
        role: 'user',
        content: userMessage
      });

      const response = await this.chat(context);

      // Сохраняем ответ в кэш
      await this.cache.set(userMessage, response);

      // Асинхронно запускаем очистку устаревших записей
      this.cache.cleanup().catch(error => {
        console.error('Error cleaning up cache:', error);
      });

      return response;
    } catch (error) {
      console.error('Error processing message:', error);
      throw error;
    }
  }
}
