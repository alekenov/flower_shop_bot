from src.services.database_service import database_service

def add_instagram_credentials():
    credentials = [
        {
            'service_name': 'instagram',
            'credential_key': 'app_id',
            'credential_value': '1106909074426380',
            'description': 'Instagram App ID for Client Support-IG'
        },
        {
            'service_name': 'instagram',
            'credential_key': 'app_secret',
            'credential_value': '1e501224dda760a4966e4cdf28e86e5b',
            'description': 'Instagram App Secret for Client Support-IG'
        }
    ]

    for cred in credentials:
        query = """
        INSERT INTO credentials (service_name, credential_key, credential_value, description)
        VALUES (%(service_name)s, %(credential_key)s, %(credential_value)s, %(description)s)
        ON CONFLICT (service_name, credential_key) 
        DO UPDATE SET 
            credential_value = EXCLUDED.credential_value,
            description = EXCLUDED.description;
        """
        database_service.execute_query(query, cred)
        print(f"✅ Добавлены учетные данные для {cred['service_name']} ({cred['credential_key']})")

if __name__ == '__main__':
    add_instagram_credentials()
