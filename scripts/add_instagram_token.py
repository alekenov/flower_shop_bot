from src.services.database_service import database_service

def add_instagram_token():
    token_data = {
        'service_name': 'instagram',
        'credential_key': 'access_token',
        'credential_value': 'EAAW4km4ocGkBO937GUcJtZBUzf11TvvWFS7t5eNbtTcqevnyQ8yJwfqCk30IAAUybq80QYPkno44LX2NH3BZBDkxfs2xvbZAQNrVd4bxyJFmrmgLTySSmrkYjs0YOFcCLtZBnWD7Fb06F4rfAPMY1yZC624oxLW3IgTd6DY8y4s7onSxJCTEW6MPBZA5NvoyqJZCkvxqU52QGkaUcrZBHQZDZD',
        'description': 'Instagram Graph API Access Token for Client Support-IG'
    }

    query = """
    INSERT INTO credentials (service_name, credential_key, credential_value, description)
    VALUES (%(service_name)s, %(credential_key)s, %(credential_value)s, %(description)s)
    ON CONFLICT (service_name, credential_key) 
    DO UPDATE SET 
        credential_value = EXCLUDED.credential_value,
        description = EXCLUDED.description;
    """
    
    database_service.execute_query(query, token_data)
    print(f"✅ Добавлен access token для Instagram")

if __name__ == '__main__':
    add_instagram_token()
