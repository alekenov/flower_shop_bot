// Follow this setup guide to integrate the Deno language server with your editor:
// https://deno.land/manual/getting_started/setup_your_environment
// This enables autocomplete, go to definition, etc.

// Setup type definitions for built-in Supabase Runtime APIs
import "jsr:@supabase/functions-js/edge-runtime.d.ts"

import { Bot, webhookCallback } from 'https://deno.land/x/grammy@v1.19.2/mod.ts'
import { Client } from 'https://deno.land/x/postgres@v0.17.0/mod.ts'

// Database connection
const dbClient = new Client({
  hostname: "aws-0-eu-central-1.pooler.supabase.com",
  port: 6543,
  database: "postgres",
  user: "postgres.dkohweivbdwweyvyvcbc",
  password: "vigkif-nesJy2-kivraq",
  tls: {
    enabled: true,
  },
})

// Initialize bot with your token
const bot = new Bot(Deno.env.get('TELEGRAM_BOT_TOKEN')!)

// Connect to database
await dbClient.connect()

// Handle /start command
bot.command('start', async (ctx) => {
  const userId = ctx.from?.id
  const message = 'Добро пожаловать в наш магазин цветов! Чем могу помочь?'
  
  await ctx.reply(message)
  
  // Log the interaction
  if (userId) {
    await dbClient.queryObject`
      INSERT INTO chat_logs (user_id, message, bot_response, context)
      VALUES (${userId}, '/start', ${message}, 'start_command')
    `
  }
})

// Handle messages
bot.on('message', async (ctx) => {
  const userId = ctx.from?.id
  const userMessage = ctx.message?.text || ''
  let botResponse = 'Извините, я вас не понял.'

  // Search in knowledge base
  const result = await dbClient.queryObject`
    SELECT answer 
    FROM knowledge_base 
    WHERE question ILIKE ${'%' + userMessage + '%'}
    LIMIT 1
  `

  if (result.rows.length > 0) {
    botResponse = result.rows[0].answer
  }

  await ctx.reply(botResponse)

  // Log the interaction
  if (userId) {
    await dbClient.queryObject`
      INSERT INTO chat_logs (user_id, message, bot_response, context)
      VALUES (${userId}, ${userMessage}, ${botResponse}, 'message')
    `
  }
})

// Handle errors
bot.catch((err) => {
  console.error('Error in bot:', err)
})

// Create webhook handler
const handleUpdate = webhookCallback(bot, 'std/http')

// Serve webhook handler
Deno.serve(async (req) => {
  try {
    const url = new URL(req.url)
    if (url.pathname.slice(1) === bot.token) {
      try {
        return await handleUpdate(req)
      } catch (err) {
        console.error(err)
        return new Response('Webhook Error')
      }
    }
    return new Response('Not found', { status: 404 })
  } catch (err) {
    console.error(err)
    return new Response('Internal Server Error', { status: 500 })
  } finally {
    // Don't close the connection as it's reused between requests
    // await dbClient.end()
  }
})

/* To invoke locally:

  1. Run `supabase start` (see: https://supabase.com/docs/reference/cli/supabase-start)
  2. Make an HTTP request:

  curl -i --location --request POST 'http://127.0.0.1:54321/functions/v1/telegram-bot' \
    --header 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0' \
    --header 'Content-Type: application/json' \
    --data '{"name":"Functions"}'

*/
