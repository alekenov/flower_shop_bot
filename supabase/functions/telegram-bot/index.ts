import { serve } from "https://deno.land/std@0.177.0/http/server.ts"
import { Bot, webhookCallback } from "https://deno.land/x/grammy@v1.17.1/mod.ts"
import { config } from "./config.ts"

// Ensure required environment variables are set
const token = Deno.env.get("TELEGRAM_BOT_TOKEN")
if (!token) {
  console.error("TELEGRAM_BOT_TOKEN environment variable is not set")
  throw new Error("TELEGRAM_BOT_TOKEN is required")
}

// Initialize bot with your authentication token
const bot = new Bot(token)

// Handle the /start command
bot.command("start", async (ctx) => {
  try {
    console.log("Handling /start command")
    await ctx.reply("Welcome to the Flower Shop Bot! 🌸\nI'm here to help you with your floral needs!")
  } catch (error) {
    console.error("Error in /start command:", error)
    await ctx.reply("Sorry, there was an error processing your command.")
  }
})

// Handle text messages
bot.on("message:text", async (ctx) => {
  try {
    console.log("Handling text message:", ctx.message.text)
    await ctx.reply("Thank you for your message! Our team will get back to you soon. 🌺")
  } catch (error) {
    console.error("Error in message handler:", error)
    await ctx.reply("Sorry, there was an error processing your message.")
  }
})

// Create webhook handler
const handleUpdate = webhookCallback(bot, "std/http")

serve(async (req) => {
  try {
    if (req.method === "POST") {
      const url = new URL(req.url)
      console.log("Received webhook request at path:", url.pathname)
      if (url.pathname === config.path) {
        return await handleUpdate(req)
      }
    }
    
    return new Response("Not found", { status: 404 })
  } catch (err) {
    console.error("Error in webhook handler:", err)
    return new Response("Internal Server Error", { 
      status: 500,
      headers: { "Content-Type": "application/json" }
    })
  }
})
