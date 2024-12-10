interface SendMessageParams {
  chat_id: number;
  text: string;
  parse_mode?: 'HTML' | 'Markdown' | 'MarkdownV2';
  reply_markup?: any;
}

interface SendChatActionParams {
  chat_id: number;
  action: 'typing' | 'upload_photo' | 'record_video' | 'upload_video' | 
          'record_audio' | 'upload_audio' | 'upload_document' | 'find_location' |
          'record_video_note' | 'upload_video_note';
}

export class TelegramClient {
  private token: string;
  private apiUrl: string;

  constructor(token: string) {
    this.token = token;
    this.apiUrl = `https://api.telegram.org/bot${token}`;
    console.log('TelegramClient initialized with API URL:', this.apiUrl);
  }

  getTokenLength(): number {
    return this.token.length;
  }

  async verifyWebhookRequest(request: Request): Promise<boolean> {
    // Для отладки временно отключаем проверку
    console.log('Webhook verification disabled for debugging');
    return true;
  }

  async sendMessage(params: SendMessageParams): Promise<Response> {
    console.log('Sending message with params:', JSON.stringify(params));
    const response = await fetch(`${this.apiUrl}/sendMessage`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params),
    });

    console.log('Telegram API response status:', response.status);
    if (!response.ok) {
      const error = await response.json();
      console.error('Telegram API error response:', error);
      throw new Error(`Telegram API error: ${JSON.stringify(error)}`);
    }

    return response;
  }

  async sendChatAction(chatId: number, action: SendChatActionParams['action']): Promise<Response> {
    const response = await fetch(`${this.apiUrl}/sendChatAction`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        chat_id: chatId,
        action: action,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Telegram API error: ${JSON.stringify(error)}`);
    }

    return response;
  }
}
