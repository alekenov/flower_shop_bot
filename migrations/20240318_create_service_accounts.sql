-- Create service_accounts table
create table if not exists public.service_accounts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    credentials JSONB NOT NULL,
    project_id VARCHAR(255),
    client_email VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Enable RLS
alter table public.service_accounts enable row level security;

-- Create policies
create policy "Service accounts are viewable by authenticated users only" 
    on public.service_accounts for select 
    using ( auth.role() = 'authenticated' );

create policy "Service accounts are insertable by authenticated users only" 
    on public.service_accounts for insert 
    with check ( auth.role() = 'authenticated' );

-- Create updated_at trigger
create or replace function public.handle_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger handle_service_accounts_updated_at
    before update on public.service_accounts
    for each row
    execute procedure public.handle_updated_at();
