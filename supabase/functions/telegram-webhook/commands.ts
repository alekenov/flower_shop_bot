import { TelegramClient } from './telegram.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.39.0';

interface CommandContext {
  chatId: number;
  text: string;
  telegram: TelegramClient;
  supabase: any; // тип будет уточнен позже
}

// Обработчик команды /start
async function handleStart({ chatId, telegram }: CommandContext) {
  await telegram.sendMessage({
    chat_id: chatId,
    text: 'Добро пожаловать в наш цветочный магазин! 🌸\n\n' +
          'Я помогу вам выбрать и заказать прекрасные цветы.\n\n' +
          'Доступные команды:\n' +
          '/products - посмотреть каталог\n' +
          '/help - получить помощь',
    parse_mode: 'HTML'
  });
}

// Обработчик команды /products
async function handleProducts({ chatId, telegram, supabase }: CommandContext) {
  try {
    const { data: products, error } = await supabase
      .from('products')
      .select('*')
      .order('name');

    if (error) throw error;

    if (!products || products.length === 0) {
      await telegram.sendMessage({
        chat_id: chatId,
        text: 'К сожалению, сейчас в каталоге нет доступных товаров.'
      });
      return;
    }

    let message = '🌺 Наш каталог:\n\n';
    products.forEach((product: any) => {
      message += `${product.name}\n`;
      message += `Цена: ${product.price} тенге\n`;
      message += `Количество: ${product.quantity} шт.\n\n`;
    });

    await telegram.sendMessage({
      chat_id: chatId,
      text: message,
      parse_mode: 'HTML'
    });
  } catch (error) {
    console.error('Error fetching products:', error);
    await telegram.sendMessage({
      chat_id: chatId,
      text: 'Произошла ошибка при получении каталога. Пожалуйста, попробуйте позже.'
    });
  }
}

// Обработчик команды /help
async function handleHelp({ chatId, telegram }: CommandContext) {
  await telegram.sendMessage({
    chat_id: chatId,
    text: '🌸 Помощь по использованию бота:\n\n' +
          '1. /start - начать работу с ботом\n' +
          '2. /products - посмотреть каталог цветов\n' +
          '3. /help - получить это сообщение\n\n' +
          'Также вы можете просто написать мне, какие цветы вас интересуют, ' +
          'и я помогу подобрать подходящий вариант.',
    parse_mode: 'HTML'
  });
}

// Карта команд
const commands: Record<string, (context: CommandContext) => Promise<void>> = {
  '/start': handleStart,
  '/products': handleProducts,
  '/help': handleHelp,
};

export async function handleCommand(command: string, context: CommandContext): Promise<void> {
  const handler = commands[command.toLowerCase()];
  if (handler) {
    await handler(context);
  } else {
    // Если команда не найдена
    await context.telegram.sendMessage({
      chat_id: context.chatId,
      text: 'Извините, я не знаю такой команды. Используйте /help для списка доступных команд.'
    });
  }
}
