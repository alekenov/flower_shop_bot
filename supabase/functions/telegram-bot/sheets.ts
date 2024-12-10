// sheets.ts
interface InventoryItem {
  name: string;
  quantity: number;
  price: number;
  description?: string;
}

export async function getInventoryData(sheetsId: string, credentials: any): Promise<InventoryItem[]> {
  try {
    console.log("Getting inventory data from sheets:", sheetsId);
    
    if (!credentials || !credentials.client_email || !credentials.private_key) {
      console.error("Invalid Google credentials:", JSON.stringify(credentials, null, 2));
      throw new Error("Invalid Google credentials");
    }

    // Create JWT token
    const jwt = {
      iss: credentials.client_email,
      scope: "https://www.googleapis.com/auth/spreadsheets.readonly",
      aud: "https://oauth2.googleapis.com/token",
      exp: Math.floor(Date.now() / 1000) + 3600,
      iat: Math.floor(Date.now() / 1000),
    };

    console.log("Created JWT:", JSON.stringify(jwt, null, 2));

    // Sign JWT
    const key = credentials.private_key;
    console.log("Processing private key...");
    
    const encoder = new TextEncoder();
    const headerPayload = btoa(JSON.stringify({
      alg: "RS256",
      typ: "JWT"
    })) + "." + btoa(JSON.stringify(jwt));

    const privateKey = await crypto.subtle.importKey(
      "pkcs8",
      new Uint8Array(
        atob(key.replace(/-----BEGIN PRIVATE KEY-----|-----END PRIVATE KEY-----|\n/g, ""))
          .split("")
          .map(c => c.charCodeAt(0))
      ),
      {
        name: "RSASSA-PKCS1-v1_5",
        hash: "SHA-256",
      },
      false,
      ["sign"]
    );

    console.log("Private key imported successfully");

    const signature = await crypto.subtle.sign(
      "RSASSA-PKCS1-v1_5",
      privateKey,
      encoder.encode(headerPayload)
    );

    console.log("JWT signed successfully");

    // Convert signature to base64
    const signatureBase64 = btoa(String.fromCharCode(...new Uint8Array(signature)));
    const jwtToken = headerPayload + "." + signatureBase64;

    // Get access token
    const tokenResponse = await fetch("https://oauth2.googleapis.com/token", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({
        grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
        assertion: jwtToken,
      }),
    });

    const tokenData = await tokenResponse.json();
    console.log("Token response:", JSON.stringify(tokenData, null, 2));

    if (!tokenData.access_token) {
      throw new Error("Failed to get access token: " + JSON.stringify(tokenData));
    }

    const { access_token } = tokenData;

    // Try different sheet names
    const sheetRanges = ['Catalog!A2:D', 'Sheet1!A2:D', 'Лист1!A2:D', 'Каталог!A2:D'];
    let values = [];

    for (const range of sheetRanges) {
      try {
        console.log(`Trying to read range: ${range}`);
        const response = await fetch(
          `https://sheets.googleapis.com/v4/spreadsheets/${sheetsId}/values/${range}`,
          {
            headers: {
              "Authorization": `Bearer ${access_token}`,
            },
          }
        );

        const data = await response.json();
        console.log(`Response for ${range}:`, JSON.stringify(data, null, 2));

        if (data.values && data.values.length > 0) {
          values = data.values;
          console.log(`Found data in range: ${range}`);
          break;
        }
      } catch (error) {
        console.warn(`Could not read from ${range}:`, error);
        continue;
      }
    }

    if (!values.length) {
      console.warn("No data found in any sheet");
      return [];
    }

    console.log("Raw data from sheets:", JSON.stringify(values, null, 2));

    // Process inventory data
    const inventory: InventoryItem[] = [];
    for (const row of values) {
      try {
        if (row.length >= 3) {
          const quantity = parseInt(row[1].trim());
          const price = parseFloat(row[2].trim());
          
          if (!isNaN(quantity) && !isNaN(price) && quantity > 0) {
            inventory.push({
              name: row[0].trim(),
              quantity,
              price,
              description: row[3]?.trim() || '',
            });
          }
        }
      } catch (error) {
        console.error("Error processing row:", row, error);
      }
    }

    console.log("Processed inventory:", JSON.stringify(inventory, null, 2));
    return inventory;
  } catch (error) {
    console.error("Error getting inventory data:", error);
    throw error;
  }
}

export function formatInventoryForBot(inventory: InventoryItem[]): string {
  if (!inventory.length) {
    return "К сожалению, информация о товарах временно недоступна.";
  }

  const items = inventory
    .filter(item => item.quantity > 0)
    .map(item => `${item.name}: ${item.quantity} шт., ${item.price} тенге${item.description ? ` (${item.description})` : ''}`);

  return "Актуальный список цветов в наличии:\n\n" + items.join("\n");
}
