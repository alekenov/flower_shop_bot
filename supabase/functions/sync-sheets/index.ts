// Follow this setup guide to integrate the Deno language server with your editor:
// https://deno.land/manual/getting_started/setup_your_environment
// This enables autocomplete, go to definition, etc.

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.39.0'
import { GoogleSpreadsheet } from 'https://esm.sh/google-spreadsheet@4.1.1'
import { JWT } from 'https://esm.sh/google-auth-library@9.4.1'
import { Product, GoogleSheetsProduct, SyncStats } from './types.ts'

// Initialize Supabase client
const supabaseUrl = Deno.env.get('SUPABASE_URL')!
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
const supabase = createClient(supabaseUrl, supabaseServiceKey)

// Initialize Google Sheets
const SPREADSHEET_ID = Deno.env.get('GOOGLE_SHEETS_SPREADSHEET_ID')!
const GOOGLE_CREDENTIALS = JSON.parse(Deno.env.get('GOOGLE_CREDENTIALS')!)

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

async function updateSupabaseProducts(products: GoogleSheetsProduct[]): Promise<SyncStats> {
  const stats: SyncStats = {
    added: 0,
    updated: 0,
    deleted: 0,
    errors: [],
  }

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
          stats.updated++
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
          stats.added++
        }
      } catch (error) {
        console.error(`Error processing product ${product.name}:`, error)
        stats.errors.push(`Failed to process ${product.name}: ${error.message}`)
      }
    }

    // Optional: Handle deletions
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
      stats.deleted = productsToDelete.length
    }

    return stats
  } catch (error) {
    console.error('Error updating Supabase products:', error)
    stats.errors.push(`Global sync error: ${error.message}`)
    return stats
  }
}

Deno.serve(async (req) => {
  try {
    // Only allow POST requests
    if (req.method !== 'POST') {
      return new Response(JSON.stringify({ error: 'Method not allowed' }), {
        status: 405,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    // Get data from Google Sheets
    const products = await getGoogleSheetsData()
    
    // Update Supabase database
    const stats = await updateSupabaseProducts(products)

    return new Response(JSON.stringify({ 
      success: true,
      stats,
      timestamp: new Date().toISOString(),
    }), {
      headers: { 'Content-Type': 'application/json' },
    })

  } catch (error) {
    console.error('Sync error:', error)
    return new Response(JSON.stringify({ 
      success: false,
      error: error.message,
      timestamp: new Date().toISOString(),
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    })
  }
})
