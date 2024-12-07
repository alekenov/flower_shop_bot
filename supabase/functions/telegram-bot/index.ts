// Follow this setup guide to integrate the Deno language server with your editor:
// https://deno.land/manual/getting_started/setup_your_environment
// This enables autocomplete, go to definition, etc.

import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { Bot, webhookCallback } from "https://deno.land/x/grammy@v1.19.2/mod.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

// Initialize Supabase client
const supabaseUrl = Deno.env.get('SUPABASE_URL')!
const supabaseKey = Deno.env.get('SUPABASE_KEY')!
const supabase = createClient(supabaseUrl, supabaseKey)

// Initialize bot with your token
const bot = new Bot(Deno.env.get('TELEGRAM_BOT_TOKEN')!)

// Handle /start command
bot.command("start", async (ctx) => {
  const userId = ctx.from?.id
  const username = ctx.from?.username
  const firstName = ctx.from?.first_name
  const lastName = ctx.from?.last_name
  
  const message = "Добро пожаловать в наш магазин цветов! \nЯ помогу вам выбрать и заказать букет."
  
  try {
    // Save user info if not exists
    if (userId) {
      await supabase
        .from('users')
        .upsert({
          id: userId,
          username,
          first_name: firstName,
          last_name: lastName
        })
    }
    
    // Log interaction
    await supabase
      .from('chat_logs')
      .insert({
        user_id: userId,
        message: '/start',
        bot_response: message,
        context: 'start_command'
      })
    
    await ctx.reply(message)
  } catch (error) {
    console.error('Error in start command:', error)
    await ctx.reply("Извините, произошла ошибка. Попробуйте позже.")
  }
})

// Handle messages
bot.on("message", async (ctx) => {
  const userId = ctx.from?.id
  const userMessage = ctx.message?.text || ''
  
  try {
    // Log incoming message
    await supabase
      .from('chat_logs')
      .insert({
        user_id: userId,
        message: userMessage,
        context: 'user_message'
      })
    
    // Default response
    const response = "Я получил ваше сообщение! Скоро научусь на него отвечать "
    
    await ctx.reply(response)
    
    // Log bot response
    await supabase
      .from('chat_logs')
      .update({ bot_response: response })
      .eq('user_id', userId)
      .is('bot_response', null)
  } catch (error) {
    console.error('Error processing message:', error)
    await ctx.reply("Извините, произошла ошибка. Попробуйте позже.")
  }
})

// Create webhook handler
const handleUpdate = webhookCallback(bot, "std/http")

serve(async (req) => {
  try {
    // Handle Telegram webhook
    if (req.method === "POST") {
      const response = await handleUpdate(req)
      return response
    }
    
    // Handle other requests
    return new Response("Hello from Telegram bot!", { status: 200 })
  } catch (error) {
    console.error("Error in webhook handler:", error)
    return new Response("Error processing request", { status: 500 })
  }
})
