import { serve } from "https://deno.land/std@0.177.0/http/server.ts"
import { Bot, webhookCallback } from "https://deno.land/x/grammy@v1.17.1/mod.ts"
import { config } from "./config.ts"

console.log("Starting Telegram bot...")

// Ensure required environment variables are set
const token = Deno.env.get("TELEGRAM_BOT_TOKEN")
const googleCredentials = JSON.parse(Deno.env.get("GOOGLE_CREDENTIALS") || "{}")
const sheetsId = Deno.env.get("GOOGLE_SHEETS_ID")

if (!token) {
  console.error("TELEGRAM_BOT_TOKEN environment variable is not set")
  throw new Error("TELEGRAM_BOT_TOKEN is required")
}

if (!sheetsId) {
  console.error("GOOGLE_SHEETS_ID environment variable is not set")
  throw new Error("GOOGLE_SHEETS_ID is required")
}

// Initialize bot with your authentication token
const bot = new Bot(token)

// Function to log message to Google Sheets
async function logToSheets(userId: string, username: string, message: string) {
  try {
    const jwt = {
      iss: googleCredentials.client_email,
      scope: "https://www.googleapis.com/auth/spreadsheets",
      aud: "https://oauth2.googleapis.com/token",
      exp: Math.floor(Date.now() / 1000) + 3600,
      iat: Math.floor(Date.now() / 1000),
    };

    // Sign JWT
    const key = googleCredentials.private_key;
    const encoder = new TextEncoder();
    const privateKey = await crypto.subtle.importKey(
      "pkcs8",
      new Uint8Array(atob(key.split("-----")[2].replace(/\\n/g, "")).split("").map(c => c.charCodeAt(0))),
      {
        name: "RSASSA-PKCS1-v1_5",
        hash: "SHA-256",
      },
      false,
      ["sign"]
    );

    const signature = await crypto.subtle.sign(
      "RSASSA-PKCS1-v1_5",
      privateKey,
      encoder.encode(JSON.stringify(jwt))
    );

    // Get access token
    const tokenResponse = await fetch("https://oauth2.googleapis.com/token", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({
        grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
        assertion: btoa(JSON.stringify(jwt)),
      }),
    });

    const { access_token } = await tokenResponse.json();

    // Log to sheets
    const now = new Date().toISOString();
    await fetch(
      `https://sheets.googleapis.com/v4/spreadsheets/${sheetsId}/values/Sheet1:append?valueInputOption=USER_ENTERED`,
      {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${access_token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          values: [[now, userId, username, message]],
        }),
      }
    );

    console.log("Successfully logged to sheets");
  } catch (error) {
    console.error("Error logging to sheets:", error);
  }
}

// Handle the /start command
bot.command("start", async (ctx) => {
  try {
    console.log("Handling /start command")
    const message = "Welcome to the Flower Shop Bot! 🌸\nI'm here to help you with your floral needs!"
    await ctx.reply(message)
    
    // Log the interaction
    await logToSheets(
      ctx.from?.id.toString() || "unknown",
      ctx.from?.username || "unknown",
      "/start"
    )
  } catch (error) {
    console.error("Error in /start command:", error)
    await ctx.reply("Sorry, there was an error processing your command.")
  }
})

// Handle text messages
bot.on("message:text", async (ctx) => {
  try {
    console.log("Handling text message:", ctx.message.text)
    const response = "Thank you for your message! Our team will get back to you soon. 🌺"
    await ctx.reply(response)
    
    // Log the interaction
    await logToSheets(
      ctx.from?.id.toString() || "unknown",
      ctx.from?.username || "unknown",
      ctx.message.text
    )
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
