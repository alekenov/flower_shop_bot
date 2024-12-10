import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.39.0'
import { TelegramClient } from './telegram.ts'
import { OpenAIClient } from './openai.ts'
import { handleCommand } from './commands.ts'
import { Logger, LogLevel, LogCategory } from './logger.ts'

interface TelegramUpdate {
  update_id: number
  message?: {
    message_id: number
    from: {
      id: number
      first_name: string
      username?: string
    }
    chat: {
      id: number
      first_name: string
      username?: string
      type: string
    }
    date: number
    text?: string
  }
}

// Инициализация клиентов
const supabaseClient = createClient(
  Deno.env.get('SUPABASE_URL') ?? '',
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
)

const logger = new Logger(supabaseClient)

const openaiClient = new OpenAIClient(
  Deno.env.get('OPENAI_API_KEY') ?? '',
  supabaseClient
)

serve(async (req) => {
  const startTime = Date.now()
  
  // Check all required environment variables
  const requiredEnvVars = [
    'TELEGRAM_BOT_TOKEN',
    'OPENAI_API_KEY',
    'SUPABASE_URL',
    'SUPABASE_SERVICE_ROLE_KEY',
    'TELEGRAM_WEBHOOK_SECRET'
  ];

  const missingEnvVars = requiredEnvVars.filter(varName => !Deno.env.get(varName));
  
  if (missingEnvVars.length > 0) {
    console.error('Missing required environment variables:', missingEnvVars);
    return new Response(JSON.stringify({
      error: 'Missing required environment variables',
      missing: missingEnvVars
    }), { status: 500 });
  }

  console.log('Request received:', {
    method: req.method,
    url: req.url,
    headers: Object.fromEntries(req.headers.entries())
  });

  console.log('Environment variables:', {
    SUPABASE_URL: Deno.env.get('SUPABASE_URL'),
    TELEGRAM_BOT_TOKEN: Deno.env.get('TELEGRAM_BOT_TOKEN')?.slice(0, 10) + '...',
    OPENAI_API_KEY: Deno.env.get('OPENAI_API_KEY')?.slice(0, 10) + '...',
  });
  
  try {
    // Проверяем, что это POST запрос
    if (req.method !== 'POST') {
      logger.warning(LogCategory.TELEGRAM, 'Invalid request method', { method: req.method })
      return new Response('Only POST requests are allowed', { status: 405 })
    }

    const telegramClient = new TelegramClient(Deno.env.get('TELEGRAM_BOT_TOKEN') ?? '')

    // Для отладки выводим заголовки запроса
    console.log('Request headers:', Object.fromEntries(req.headers.entries()))

    // Временно отключаем проверку webhook для отладки
    const isValidRequest = await telegramClient.verifyWebhookRequest(req)
    if (!isValidRequest) {
      logger.error(LogCategory.TELEGRAM, 'Invalid webhook request')
      return new Response('Unauthorized', { status: 401 })
    }

    const update: TelegramUpdate = await req.json()
    console.log('Received update:', JSON.stringify(update))

    // Проверяем наличие сообщения
    if (!update.message) {
      logger.warning(LogCategory.TELEGRAM, 'No message in update', { update })
      return new Response('No message in update', { status: 400 })
    }

    const { message } = update
    const chatId = message.chat.id
    const userId = message.from?.id
    const text = message.text ?? ''

    // Устанавливаем контекст для логов
    logger.setContext({
      chatId,
      userId,
      username: message.from?.username,
      updateId: update.update_id
    })

    // Логируем полученное сообщение
    logger.info(LogCategory.TELEGRAM, 'Received message', {
      messageId: message.message_id,
      text
    })

    try {
      // Обрабатываем команду или текстовое сообщение
      if (text.startsWith('/')) {
        // Это команда
        logger.info(LogCategory.TELEGRAM, 'Processing command', {
          command: text.split(' ')[0]
        })

        await handleCommand(text.split(' ')[0], {
          chatId,
          text,
          telegram: telegramClient,
          supabase: supabaseClient
        })
      } else {
        // Отправляем "печатает" статус
        await telegramClient.sendChatAction(chatId, 'typing')
        
        logger.info(LogCategory.OPENAI, 'Processing text message', {
          messageLength: text.length
        })

        // Засекаем время обработки
        const aiStartTime = Date.now()
        
        // Обрабатываем текстовое сообщение через OpenAI
        const response = await openaiClient.processUserMessage(text)
        
        // Логируем время обработки
        const aiProcessingTime = Date.now() - aiStartTime
        await logger.logMetric('ai_processing_time', aiProcessingTime, {
          chat_id: chatId.toString()
        })
        
        // Отправляем ответ пользователю
        await telegramClient.sendMessage({
          chat_id: chatId,
          text: response,
          parse_mode: 'HTML'
        })

        logger.info(LogCategory.TELEGRAM, 'Sent response', {
          responseLength: response.length,
          processingTime: aiProcessingTime
        })
      }
    } catch (error) {
      logger.error(LogCategory.GENERAL, 'Error processing message', {
        error: error.message,
        stack: error.stack
      })
      
      // Отправляем сообщение об ошибке пользователю
      await telegramClient.sendMessage({
        chat_id: chatId,
        text: 'Извините, произошла ошибка при обработке вашего сообщения. Пожалуйста, попробуйте позже.'
      })
    }

    // Логируем общее время обработки
    const totalProcessingTime = Date.now() - startTime
    await logger.logMetric('total_processing_time', totalProcessingTime, {
      chat_id: chatId.toString()
    })

    // Очищаем контекст логгера
    logger.clearContext()

    // Отправляем успешный ответ
    return new Response(JSON.stringify({
      status: 'success',
      message: 'Update processed'
    }), {
      headers: { 'Content-Type': 'application/json' }
    })

  } catch (error) {
    // Обработка ошибок
    logger.error(LogCategory.GENERAL, 'Fatal error processing update', {
      error: error.message,
      stack: error.stack
    })

    return new Response(JSON.stringify({
      status: 'error',
      message: error.message
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    })
  }
})
