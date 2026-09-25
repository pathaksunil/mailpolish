-- Create custom types for licensing tiers
create type user_tier as enum ('free', 'pro');

-- User Profiles Table linked to Supabase Auth
create table public.user_profiles (
  id uuid references auth.users on delete cascade primary key,
  email text not null,
  tier user_tier default 'free' not null,
  tokens_used_today integer default 0 not null,
  last_reset_date date default current_date not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable Row Level Security (RLS)
alter table public.user_profiles enable row level security;

-- Policy: Users can view and update their own profile
create policy "Users can view own profile" 
  on public.user_profiles for select 
  using (auth.uid() = id);

create policy "Users can update own profile" 
  on public.user_profiles for update 
  using (auth.uid() = id);

-- Automatic Trigger Function to Initialize Profile on Signup
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.user_profiles (id, email, tier, tokens_used_today)
  values (new.id, new.email, 'free', 0);
  return new;
end;
$$ language plpgsql security definer;

-- Trigger execution on auth.users creation
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();