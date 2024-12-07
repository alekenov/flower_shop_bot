import { serve } from "https://deno.land/std@0.177.0/http/server.ts"
import { Bot, webhookCallback } from "https://deno.land/x/grammy@v1.17.1/mod.ts"

// Initialize bot with your authentication token
const bot = new Bot(Deno.env.get("TELEGRAM_BOT_TOKEN") || "")

// Handle the /start command
bot.command("start", async (ctx) => {
  await ctx.reply("Welcome to the Flower Shop Bot! 🌸")
})

// Handle text messages
bot.on("message:text", async (ctx) => {
  await ctx.reply("Thank you for your message! Our team will get back to you soon.")
})

// Create webhook handler
const handleUpdate = webhookCallback(bot, "std/http")

serve(async (req) => {
  try {
    const url = new URL(req.url)
    if (url.pathname.slice(1) === bot.token) {
      return await handleUpdate(req)
    }
    return new Response("Not found", { status: 404 })
  } catch (err) {
    console.error(err)
    return new Response("Internal Server Error", { status: 500 })
  }
})
