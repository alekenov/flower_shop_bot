# Google Sheets Sync Function

This Edge Function synchronizes product data between Google Sheets and your Supabase database.

## Setup

1. Set up the required environment variables in your Supabase project:
   ```bash
   supabase secrets set GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id
   supabase secrets set GOOGLE_CREDENTIALS='{"type": "service_account", ...}'
   ```

2. Make sure your Google Sheets has a sheet named "Catalog" with the following columns:
   - name
   - quantity
   - price
   - description (optional)
   - category (optional)

3. Deploy the function:
   ```bash
   supabase functions deploy sync-sheets
   ```

## Usage

Trigger the sync with a POST request:

```bash
curl -i --location --request POST 'https://[YOUR_PROJECT_REF].supabase.co/functions/v1/sync-sheets' \
  --header 'Authorization: Bearer [YOUR_ANON_KEY]'
```

## Response Format

Success response:
```json
{
  "success": true,
  "stats": {
    "added": 5,
    "updated": 10,
    "deleted": 2,
    "errors": []
  },
  "timestamp": "2023-12-10T12:00:00Z"
}
```

Error response:
```json
{
  "success": false,
  "error": "Error message",
  "timestamp": "2023-12-10T12:00:00Z"
}
```

## Scheduling

To run the sync automatically, you can set up a cron job using services like GitHub Actions or any other scheduler to make the POST request at regular intervals.
