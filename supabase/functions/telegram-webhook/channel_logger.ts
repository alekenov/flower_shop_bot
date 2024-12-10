import { TelegramClient } from './telegram.ts';

export class ChannelLogger {
  private telegramClient: TelegramClient;
  private channelId: string;

  constructor(telegramClient: TelegramClient, channelId: string) {
    this.telegramClient = telegramClient;
    this.channelId = channelId;
  }

  async logInteraction(userId: number, username: string | undefined, question: string, answer: string, responseType: string = 'Normal') {
    const message = `🤖 Bot Interaction Log\n\n` +
      `👤 User: ${username || 'Anonymous'} (ID: ${userId})\n` +
      `❓ Question:\n${question}\n\n` +
      `✍️ Answer:\n${answer}\n\n` +
      `📊 Response Type: ${responseType}\n` +
      `-----------------------------------`;

    try {
      await this.telegramClient.sendMessage({
        chat_id: parseInt(this.channelId),
        text: message,
        parse_mode: 'HTML'
      });
    } catch (error) {
      console.error('Error sending log to channel:', error);
    }
  }
}
