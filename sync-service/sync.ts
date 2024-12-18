import { createClient } from '@supabase/supabase-js'
import { GoogleSpreadsheet } from 'google-spreadsheet'
import { JWT } from 'google-auth-library'
import dotenv from 'dotenv'
import { Product, GoogleSheetsProduct } from '../supabase/functions/sync-sheets/types'

dotenv.config()

const SYNC_INTERVAL = 60000 // 60 seconds in milliseconds

// Initialize Supabase client
const supabaseUrl = process.env.SUPABASE_URL!
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!
const supabase = createClient(supabaseUrl, supabaseServiceKey)

// Initialize Google Sheets
const SPREADSHEET_ID = process.env.GOOGLE_SHEETS_SPREADSHEET_ID!
const GOOGLE_CREDENTIALS = JSON.parse(process.env.GOOGLE_CREDENTIALS!)

async function getGoogleSheetsData(): Promise<GoogleSheetsProduct[]> {
  try {
    const jwt = new JWT({
      email: GOOGLE_CREDENTIALS.client_email,
      key: GOOGLE_CREDENTIALS.private_key,
      scopes: ['https://www.googleapis.com/auth/spreadsheets.readonly'],
    })

    const doc = new GoogleSpreadsheet(SPREADSHEET_ID, jwt)
    await doc.loadInfo()
    
    const sheet = doc.sheetsByTitle['Catalog']
    if (!sheet) {
      throw new Error('Catalog sheet not found')
    }

    await sheet.loadCells()
    const rows = await sheet.getRows()
    
    return rows.map(row => ({
      name: row.get('name'),
      quantity: parseInt(row.get('quantity')) || 0,
      price: parseFloat(row.get('price')) || 0,
      description: row.get('description'),
      category: row.get('category'),
    }))
  } catch (error) {
    console.error('Error fetching Google Sheets data:', error)
    throw error
  }
}

async function updateSupabaseProducts(products: GoogleSheetsProduct[]) {
  try {
    // Get existing products from Supabase
    const { data: existingProducts, error: fetchError } = await supabase
      .from('products')
      .select('id, name')

    if (fetchError) {
      throw fetchError
    }

    const existingProductMap = new Map(
      existingProducts?.map(p => [p.name.toLowerCase(), p.id]) || []
    )

    let added = 0, updated = 0, deleted = 0, errors: string[] = []

    // Process each product from Google Sheets
    for (const product of products) {
      try {
        const productName = product.name.toLowerCase()
        const existingId = existingProductMap.get(productName)

        if (existingId) {
          // Update existing product
          const { error: updateError } = await supabase
            .from('products')
            .update({
              quantity: product.quantity,
              price: product.price,
              description: product.description,
              category: product.category,
              last_synced_at: new Date().toISOString(),
            })
            .eq('id', existingId)

          if (updateError) throw updateError
          updated++
        } else {
          // Insert new product
          const { error: insertError } = await supabase
            .from('products')
            .insert({
              name: product.name,
              quantity: product.quantity,
              price: product.price,
              description: product.description,
              category: product.category,
              last_synced_at: new Date().toISOString(),
            })

          if (insertError) throw insertError
          added++
        }
      } catch (error) {
        console.error(`Error processing product ${product.name}:`, error)
        errors.push(`Failed to process ${product.name}: ${error.message}`)
      }
    }

    // Handle deletions
    const googleSheetsNames = new Set(products.map(p => p.name.toLowerCase()))
    const productsToDelete = existingProducts?.filter(
      p => !googleSheetsNames.has(p.name.toLowerCase())
    )

    if (productsToDelete && productsToDelete.length > 0) {
      const { error: deleteError } = await supabase
        .from('products')
        .delete()
        .in('id', productsToDelete.map(p => p.id))

      if (deleteError) {
        throw deleteError
      }
      deleted = productsToDelete.length
    }

    return { added, updated, deleted, errors }
  } catch (error) {
    console.error('Error updating Supabase products:', error)
    return {
      added: 0,
      updated: 0,
      deleted: 0,
      errors: [`Global sync error: ${error.message}`]
    }
  }
}

async function syncLoop() {
  while (true) {
    try {
      console.log('Starting sync...', new Date().toISOString())
      const products = await getGoogleSheetsData()
      const stats = await updateSupabaseProducts(products)
      console.log('Sync completed:', stats)
    } catch (error) {
      console.error('Sync failed:', error)
    }

    // Wait for the next sync interval
    await new Promise(resolve => setTimeout(resolve, SYNC_INTERVAL))
  }
}

// Start the sync loop
console.log('Starting sync service...')
syncLoop().catch(console.error)
