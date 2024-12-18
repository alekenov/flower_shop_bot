import { serve } from "https://deno.land/std@0.177.0/http/server.ts"
import { Bot } from "https://deno.land/x/grammy@v1.17.1/mod.ts"

console.log("Starting Telegram bot...")

// Initialize Google Sheets client
async function getInventoryData() {
  try {
    console.log("Starting getInventoryData...")
    const credentialsStr = Deno.env.get("GOOGLE_CREDENTIALS")
    if (!credentialsStr) {
      console.error("GOOGLE_CREDENTIALS environment variable is not set")
      return []
    }

    let credentials
    try {
      credentials = JSON.parse(credentialsStr)
      console.log("Successfully parsed credentials")
    } catch (e) {
      console.error("Failed to parse GOOGLE_CREDENTIALS:", e)
      return []
    }

    if (!credentials.client_email || !credentials.private_key) {
      console.error("Invalid credentials format:", credentials)
      return []
    }

    const spreadsheetId = Deno.env.get("GOOGLE_SHEETS_SPREADSHEET_ID")
    if (!spreadsheetId) {
      console.error("GOOGLE_SHEETS_SPREADSHEET_ID not set")
      return []
    }
    
    console.log("Getting data from spreadsheet:", spreadsheetId)
    
    const token = await fetch("https://oauth2.googleapis.com/token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
        assertion: await createJWT(credentials)
      })
    }).then(r => r.json())

    console.log("Got Google token:", token)

    if (!token.access_token) {
      console.error("No access token in response:", token)
      return []
    }

    const sheetsResponse = await fetch(
      `https://sheets.googleapis.com/v4/spreadsheets/${spreadsheetId}/values/catalog!A2:E`,
      {
        headers: {
          Authorization: `Bearer ${token.access_token}`
        }
      }
    )
    
    console.log("Sheets response status:", sheetsResponse.status)
    const sheets = await sheetsResponse.json()
    console.log("Got sheets data:", JSON.stringify(sheets, null, 2))

    if (!sheets.values) {
      console.error("No values in sheets response:", sheets)
      return []
    }

    return sheets.values
  } catch (error) {
    console.error("Error getting inventory data:", error)
    return []
  }
}

async function createJWT(credentials: any) {
  try {
    const header = btoa(JSON.stringify({
      alg: "RS256",
      typ: "JWT"
    }))

    const now = Math.floor(Date.now() / 1000)
    const claim = btoa(JSON.stringify({
      iss: credentials.client_email,
      scope: "https://www.googleapis.com/auth/spreadsheets.readonly",
      aud: "https://oauth2.googleapis.com/token",
      exp: now + 3600,
      iat: now
    }))

    // Clean up the private key
    const privateKeyPEM = credentials.private_key
      .replace(/-----BEGIN PRIVATE KEY-----\n/, '')
      .replace(/\n-----END PRIVATE KEY-----\n?/, '')
      .replace(/\n/g, '')

    // Convert from base64 to ArrayBuffer
    const binaryString = atob(privateKeyPEM)
    const bytes = new Uint8Array(binaryString.length)
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i)
    }

    const key = await crypto.subtle.importKey(
      "pkcs8",
      bytes,
      {
        name: "RSASSA-PKCS1-v1_5",
        hash: "SHA-256"
      },
      false,
      ["sign"]
    )

    const signature = await crypto.subtle.sign(
      "RSASSA-PKCS1-v1_5",
      key,
      new TextEncoder().encode(`${header}.${claim}`)
    )

    return `${header}.${claim}.${btoa(String.fromCharCode(...new Uint8Array(signature)))}`
  } catch (error) {
    console.error("Error creating JWT:", error)
    throw error
  }
}

async function askOpenAI(question: string, inventory: any[]) {
  try {
    const inventoryText = inventory.map(([name, quantity, price, description]) => 
      `${name}: ${description}, цена ${price} тг, количество ${quantity} шт`
    ).join("\n")

    const response = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${Deno.env.get("OPENAI_API_KEY")}`
      },
      body: JSON.stringify({
        model: "gpt-3.5-turbo",
        messages: [
          {
            role: "system",
            content: `Ты - помощник цветочного магазина. Вот текущий инвентарь:\n${inventoryText}\n\nОтвечай на вопросы клиентов о наличии и ценах на цветы. Отвечай кратко и по существу. Используй только информацию из инвентаря выше. В ответе обязательно указывай длину стебля и другие важные характеристики из описания, если они есть.`
          },
          {
            role: "user",
            content: question
          }
        ],
        temperature: 0.7,
        max_tokens: 200
      })
    }).then(r => r.json())

    return response.choices[0].message.content
  } catch (error) {
    console.error("OpenAI error:", error)
    return null
  }
}

const bot = new Bot(Deno.env.get("TELEGRAM_BOT_TOKEN") || "")

serve(async (req) => {
  try {
    if (req.method === "POST") {
      const body = await req.json()
      console.log("Received update:", JSON.stringify(body, null, 2))

      if (body.message?.text) {
        const chatId = body.message.chat.id
        const text = body.message.text.toLowerCase()

        let response = ""
        if (text === "/start") {
          response = "Привет! Я помогу вам узнать о наличии цветов. Просто спросите меня о конкретном цветке или напишите 'что есть в наличии?'"
        } else {
          const inventory = await getInventoryData()
          console.log("Got inventory:", inventory)

          if (inventory.length > 0) {
            if (text === "что есть в наличии?") {
              response = "Сейчас в наличии:\n\n"
              const uniqueFlowers = new Map()
              
              for (const [name, quantity, price, description] of inventory) {
                if (quantity && parseInt(quantity) > 0) {
                  // Используем описание как уникальный идентификатор
                  uniqueFlowers.set(description, `${name} - ${price} тг\n${description}\nВ наличии: ${quantity} шт\n`)
                }
              }
              
              response += Array.from(uniqueFlowers.values()).join("\n")
            } else {
              // Используем OpenAI для более умного ответа
              const aiResponse = await askOpenAI(text, inventory)
              if (aiResponse) {
                response = aiResponse
              } else {
                // Fallback если OpenAI не ответил
                const searchText = text.replace(/есть|сколько стоит|цена/gi, "").trim()
                const flowers = inventory.filter(([name, quantity]) => 
                  name.toLowerCase().includes(searchText) && parseInt(quantity) > 0
                )
                
                if (flowers.length > 0) {
                  response = "Нашел следующие варианты:\n\n"
                  flowers.forEach(([name, quantity, price, description]) => {
                    response += `${name}\n${description}\nЦена: ${price} тг\nВ наличии: ${quantity} шт\n\n`
                  })
                } else {
                  response = "Извините, я не нашел такой цветок. Попробуйте спросить по-другому или напишите 'что есть в наличии?'"
                }
              }
            }
          } else {
            response = "Извините, не могу получить данные об инвентаре. Попробуйте позже."
          }
        }

        await fetch(`https://api.telegram.org/bot${Deno.env.get("TELEGRAM_BOT_TOKEN")}/sendMessage`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            chat_id: chatId,
            text: response,
          }),
        })
      }
    }
    
    return new Response("OK", { status: 200 })
  } catch (err) {
    console.error("Error in webhook handler:", err)
    return new Response(JSON.stringify({ error: err.message }), { 
      status: 200,  // Always return 200 to Telegram
      headers: { "Content-Type": "application/json" }
    })
  }
})
