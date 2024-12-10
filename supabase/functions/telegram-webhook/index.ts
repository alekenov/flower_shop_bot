// Follow this setup guide to integrate the Deno language server with your editor:
// https://deno.land/manual/getting_started/setup_your_environment
// This enables autocomplete, go to definition, etc.

// @supabase/functions-js v2.1.5
// deno-lint-ignore-file
// @ts-nocheck

import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.39.0'
import { TelegramClient } from './telegram.ts'
import { OpenAIClient } from './openai.ts'
import { Logger, LogLevel, LogCategory } from './logger.ts'
import { ChannelLogger } from './channel_logger.ts'

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

serve(async (req) => {
  console.log('Request received:', {
    method: req.method,
    url: req.url,
    headers: Object.fromEntries(req.headers.entries())
  });

  try {
    const bodyText = await req.text();
    console.log('Raw request body:', bodyText);

    if (req.method !== 'POST') {
      console.warn('Invalid request method:', req.method);
      return new Response('Only POST requests are allowed', { status: 405 });
    }

    // Инициализируем Supabase клиент
    const supabaseUrl = Deno.env.get('SUPABASE_URL');
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');
    const telegramToken = Deno.env.get('TELEGRAM_BOT_TOKEN');
    const openaiKey = Deno.env.get('OPENAI_API_KEY');

    console.log('Environment variables check:', {
      hasSupabaseUrl: !!supabaseUrl,
      hasSupabaseKey: !!supabaseKey,
      hasTelegramToken: !!telegramToken,
      hasOpenAiKey: !!openaiKey,
      supabaseUrlLength: supabaseUrl?.length,
      telegramTokenLength: telegramToken?.length,
    });

    if (!supabaseUrl || !supabaseKey) {
      throw new Error('Missing Supabase credentials');
    }

    if (!telegramToken) {
      throw new Error('Missing Telegram Bot Token');
    }

    if (!openaiKey) {
      throw new Error('Missing OpenAI API Key');
    }

    const supabase = createClient(supabaseUrl, supabaseKey);
    const logger = new Logger(supabase);
    const telegramClient = new TelegramClient(telegramToken);
    const openai = new OpenAIClient(openaiKey, supabase);
    
    // Инициализируем логгер для канала
    const channelLogger = new ChannelLogger(
      telegramClient,
      Deno.env.get('TELEGRAM_LOG_CHANNEL_ID') || ''
    );

    console.log('Clients initialized');

    let update: TelegramUpdate;
    try {
      update = JSON.parse(bodyText);
      console.log('Parsed update:', update);
    } catch (e) {
      console.error('Failed to parse JSON:', e);
      logger.error(LogCategory.TELEGRAM, 'Failed to parse JSON', { error: e.message, body: bodyText });
      return new Response('Invalid JSON', { status: 400 });
    }

    logger.info(LogCategory.TELEGRAM, 'Received update', { update });

    if (!update.message) {
      console.warn('No message in update:', update);
      logger.warning(LogCategory.TELEGRAM, 'No message in update', { update });
      return new Response('No message in update', { status: 400 });
    }

    const chatId = update.message.chat.id;
    const userId = update.message.from?.id;
    const userName = update.message.from?.username;
    const messageText = update.message.text || '';

    console.log('Message info:', {
      chatId,
      userId,
      userName,
      messageText
    });

    // Устанавливаем контекст для логов
    logger.setContext({
      chat_id: chatId,
      user_id: userId,
      user_name: userName
    });

    logger.info(LogCategory.TELEGRAM, 'Processing message', { 
      chat_id: chatId,
      user_id: userId,
      user_name: userName,
      message_text: messageText 
    });

    const startTime = Date.now();

    try {
      // Обработка команд
      if (messageText.startsWith('/')) {
        const command = messageText.split(' ')[0].toLowerCase();
        console.log('Processing command:', command);
        logger.info(LogCategory.TELEGRAM, `Processing command: ${command}`, { command });

        switch (command) {
          case '/start':
            console.log('Sending start message');
            await telegramClient.sendMessage({
              chat_id: chatId,
              text: 'Добро пожаловать в цветочный магазин! Чем могу помочь?'
            });
            console.log('Start message sent');
            break;
          default:
            console.log('Sending unknown command message');
            await telegramClient.sendMessage({
              chat_id: chatId,
              text: 'Извините, я не знаю такой команды.'
            });
            console.log('Unknown command message sent');
            logger.warning(LogCategory.TELEGRAM, 'Unknown command', { command });
        }
      } else {
        // Обработка обычных сообщений через OpenAI
        try {
          console.log('Processing message with OpenAI');
          logger.info(LogCategory.OPENAI, 'Processing message with OpenAI', { message: messageText });
          
          console.log('Calling OpenAI');
          const response = await openai.processUserMessage(messageText);
          console.log('OpenAI response received:', response);

          console.log('Sending message to Telegram');
          await telegramClient.sendMessage({
            chat_id: chatId,
            text: response
          });
          console.log('Message sent to Telegram');

          // Логируем в канал
          await channelLogger.logInteraction(
            userId || 0,
            userName || 'Anonymous',
            messageText,
            response
          );
          
          // Логируем успешную обработку
          logger.info(LogCategory.OPENAI, 'Successfully processed message', { 
            input: messageText,
            response_length: response.length
          });

          // Логируем метрику времени обработки
          const processingTime = Date.now() - startTime;
          await logger.logMetric('message_processing_time', processingTime, {
            type: 'openai_response',
            chat_id: String(chatId),
            user_id: String(userId)
          });
        } catch (error) {
          console.error('Error in OpenAI processing:', error);
          logger.error(LogCategory.OPENAI, 'Error processing message with OpenAI', {
            error: error.message,
            stack: error.stack,
            input: messageText
          });
          
          console.log('Sending error message to Telegram');
          await telegramClient.sendMessage({
            chat_id: chatId,
            text: 'Извините, произошла ошибка при обработке вашего сообщения.'
          });
          console.log('Error message sent to Telegram');
        }
      }

      return new Response('OK', { status: 200 });
    } catch (error) {
      console.error('Unhandled error in webhook:', error);
      logger.error(LogCategory.GENERAL, 'Unhandled error in webhook', {
        error: error.message,
        stack: error.stack
      });
      return new Response(error.message, { status: 500 });
    } finally {
      logger.clearContext();
    }
  } catch (error) {
    console.error('Critical error:', error);
    return new Response('Internal Server Error', { status: 500 });
  }
});
