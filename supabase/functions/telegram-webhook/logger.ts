import { SupabaseClient } from 'https://esm.sh/@supabase/supabase-js@2.39.0';

export enum LogLevel {
  DEBUG = 'DEBUG',
  INFO = 'INFO',
  WARNING = 'WARNING',
  ERROR = 'ERROR'
}

export enum LogCategory {
  TELEGRAM = 'TELEGRAM',
  OPENAI = 'OPENAI',
  CACHE = 'CACHE',
  DATABASE = 'DATABASE',
  GENERAL = 'GENERAL'
}

interface LogEntry {
  id?: number;
  level: LogLevel;
  category: LogCategory;
  message: string;
  metadata?: Record<string, any>;
  user_id?: number;
  chat_id?: number;
  created_at?: string;
}

export class Logger {
  private supabase: SupabaseClient;
  private tableName: string = 'bot_logs';
  private context: Record<string, any> = {};

  constructor(supabase: SupabaseClient) {
    this.supabase = supabase;
  }

  // Установка контекста для всех последующих логов
  setContext(context: Record<string, any>) {
    this.context = { ...this.context, ...context };
  }

  // Очистка контекста
  clearContext() {
    this.context = {};
  }

  private async writeLog(entry: LogEntry) {
    try {
      // Проверяем подключение к базе данных
      const { data: healthCheck, error: healthError } = await this.supabase
        .from('bot_logs')
        .select('id')
        .limit(1);

      if (healthError) {
        console.error('Database connection error:', healthError);
        return;
      }

      // Добавляем контекст к метаданным
      const metadata = {
        ...this.context,
        ...entry.metadata,
        timestamp: new Date().toISOString(),
        environment: Deno.env.get('ENVIRONMENT') || 'development'
      };

      console.log('Attempting to write log to database:', {
        table: this.tableName,
        entry: { ...entry, metadata }
      });

      const { data, error } = await this.supabase
        .from(this.tableName)
        .insert([{
          level: entry.level,
          category: entry.category,
          message: entry.message,
          metadata: metadata,
          user_id: this.context.user_id,
          chat_id: this.context.chat_id,
          created_at: new Date().toISOString()
        }]);

      if (error) {
        console.error('Error writing to log:', {
          error,
          errorMessage: error.message,
          errorDetails: error.details,
          entry: { ...entry, metadata }
        });
      } else {
        console.log('Successfully wrote log to database:', data);
      }

      // Также выводим в консоль для локальной разработки
      const logMessage = `[${entry.level}] [${entry.category}] ${entry.message}`;
      switch (entry.level) {
        case LogLevel.ERROR:
          console.error(logMessage, metadata);
          break;
        case LogLevel.WARNING:
          console.warn(logMessage, metadata);
          break;
        case LogLevel.INFO:
          console.info(logMessage, metadata);
          break;
        default:
          console.log(logMessage, metadata);
      }
    } catch (error) {
      console.error('Error in logger:', {
        error,
        errorMessage: error.message,
        errorStack: error.stack,
        entry
      });
    }
  }

  debug(category: LogCategory, message: string, metadata?: Record<string, any>) {
    this.writeLog({
      level: LogLevel.DEBUG,
      category,
      message,
      metadata
    });
  }

  info(category: LogCategory, message: string, metadata?: Record<string, any>) {
    this.writeLog({
      level: LogLevel.INFO,
      category,
      message,
      metadata
    });
  }

  warning(category: LogCategory, message: string, metadata?: Record<string, any>) {
    this.writeLog({
      level: LogLevel.WARNING,
      category,
      message,
      metadata
    });
  }

  error(category: LogCategory, message: string, metadata?: Record<string, any>) {
    this.writeLog({
      level: LogLevel.ERROR,
      category,
      message,
      metadata
    });
  }

  // Метод для логирования метрик
  async logMetric(name: string, value: number, tags?: Record<string, string>) {
    try {
      console.log('Attempting to write metric to database:', {
        table: 'bot_metrics',
        metric: { name, value, tags }
      });

      const { data, error } = await this.supabase
        .from('bot_metrics')
        .insert({
          name,
          value,
          tags,
          timestamp: new Date().toISOString()
        });

      if (error) {
        console.error('Error logging metric:', error);
      } else {
        console.log('Successfully wrote metric to database:', data);
      }
    } catch (error) {
      console.error('Error in metric logger:', error);
    }
  }
}
