import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.39.0'
import { google } from 'npm:googleapis'

// Конфигурация
const SUPABASE_URL = Deno.env.get('SUPABASE_URL')
const SUPABASE_KEY = Deno.env.get('SUPABASE_KEY')
const GOOGLE_SHEETS_SPREADSHEET_ID = Deno.env.get('GOOGLE_SHEETS_SPREADSHEET_ID')
const GOOGLE_DOCS_KNOWLEDGE_BASE_ID = Deno.env.get('GOOGLE_DOCS_KNOWLEDGE_BASE_ID')

if (!SUPABASE_URL || !SUPABASE_KEY || !GOOGLE_SHEETS_SPREADSHEET_ID || !GOOGLE_DOCS_KNOWLEDGE_BASE_ID) {
  console.error('Missing required environment variables')
  Deno.exit(1)
}

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY)

// Аутентификация Google
const auth = new google.auth.GoogleAuth({
  keyFile: './google_sheets_credentials.json',
  scopes: [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/documents.readonly',
  ],
})

// Миграция продуктов из Google Sheets
async function migrateProducts() {
  const sheets = google.sheets({ version: 'v4', auth })
  
  console.log('Fetching products from Google Sheets...')
  const response = await sheets.spreadsheets.values.get({
    spreadsheetId: GOOGLE_SHEETS_SPREADSHEET_ID,
    range: 'Products!A2:F', // Предполагаем, что первая строка - заголовки
  })

  const rows = response.data.values
  if (!rows || rows.length === 0) {
    console.log('No products found in Google Sheets')
    return
  }

  console.log(`Found ${rows.length} products. Migrating to Supabase...`)
  
  for (const row of rows) {
    const [name, description, price, category, imageUrl, inStock] = row
    
    const { error } = await supabase
      .from('products')
      .upsert({
        name,
        description,
        price: parseFloat(price),
        category,
        image_url: imageUrl,
        in_stock: inStock === 'TRUE'
      })

    if (error) {
      console.error(`Error migrating product ${name}:`, error)
    }
  }

  console.log('Products migration completed')
}

// Миграция базы знаний из Google Docs
async function migrateKnowledgeBase() {
  const docs = google.docs({ version: 'v1', auth })
  
  console.log('Fetching knowledge base from Google Docs...')
  const doc = await docs.documents.get({
    documentId: GOOGLE_DOCS_KNOWLEDGE_BASE_ID
  })

  if (!doc.data.body) {
    console.log('No content found in Google Docs')
    return
  }

  // Извлекаем текст из документа
  let content = ''
  const elements = doc.data.body.content
  elements?.forEach(element => {
    if (element.paragraph) {
      element.paragraph.elements?.forEach(el => {
        if (el.textRun?.content) {
          content += el.textRun.content
        }
      })
    }
  })

  console.log('Migrating knowledge base to Supabase...')
  
  const { error } = await supabase
    .from('knowledge_base')
    .upsert({
      title: doc.data.title || 'Main Knowledge Base',
      content,
      category: 'general',
      tags: ['migrated', 'google-docs']
    })

  if (error) {
    console.error('Error migrating knowledge base:', error)
  } else {
    console.log('Knowledge base migration completed')
  }
}

// Запуск миграции
async function main() {
  try {
    await migrateProducts()
    await migrateKnowledgeBase()
    console.log('Migration completed successfully')
  } catch (error) {
    console.error('Migration failed:', error)
    Deno.exit(1)
  }
}

main()
