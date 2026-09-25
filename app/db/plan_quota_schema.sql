-- Run in the Supabase SQL editor before deploying quota-enabled API code.
create table if not exists public.plans (
  code text primary key,
  display_name text not null,
  stripe_price_id text unique
);

create table if not exists public.plan_entitlements (
  plan_code text not null references public.plans(code) on delete cascade,
  provider text not null check (provider in ('groq', 'ollama')),
  daily_token_limit integer not null check (daily_token_limit > 0),
  monthly_token_limit integer not null check (monthly_token_limit > 0),
  primary key (plan_code, provider)
);

alter table public.subscriptions add column if not exists plan_code text references public.plans(code);

create table if not exists public.generation_usage (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  provider text not null check (provider in ('groq', 'ollama')),
  model text,
  status text not null check (status in ('reserved', 'succeeded', 'failed')),
  reserved_tokens integer not null default 0,
  prompt_tokens integer not null default 0,
  completion_tokens integer not null default 0,
  total_tokens integer not null default 0,
  billing_period_end timestamptz not null,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);
create index if not exists generation_usage_user_provider_created_idx
  on public.generation_usage (user_id, provider, created_at desc);

insert into public.plans (code, display_name) values
  ('pro', 'Pro'), ('ultra', 'Ultra'), ('private_ai', 'Private AI')
on conflict (code) do update set display_name = excluded.display_name;

insert into public.plan_entitlements values
  ('pro', 'groq', 15000, 450000),
  ('ultra', 'groq', 25000, 750000),
  ('ultra', 'ollama', 40000, 1200000),
  ('private_ai', 'ollama', 40000, 1200000)
on conflict (plan_code, provider) do update set
  daily_token_limit = excluded.daily_token_limit,
  monthly_token_limit = excluded.monthly_token_limit;

create or replace function public.reserve_generation_quota(
  p_user_id uuid, p_provider text, p_model text, p_reserved_tokens integer
) returns table (usage_id uuid) language plpgsql security definer as $$
declare
  v_subscription public.subscriptions%rowtype;
  v_daily_limit integer;
  v_monthly_limit integer;
  v_daily_used integer;
  v_monthly_used integer;
begin
  if p_reserved_tokens <= 0 then raise exception 'Reserved tokens must be positive'; end if;
  select * into v_subscription from public.subscriptions
    where user_id = p_user_id and status = 'active' and current_period_end > now()
    order by updated_at desc nulls last limit 1;
  if not found or v_subscription.plan_code is null then raise exception 'No active plan'; end if;
  select daily_token_limit, monthly_token_limit into v_daily_limit, v_monthly_limit
    from public.plan_entitlements where plan_code = v_subscription.plan_code and provider = p_provider;
  if not found then raise exception 'Plan does not include requested provider'; end if;
  perform pg_advisory_xact_lock(hashtext(p_user_id::text || ':' || p_provider));
  select coalesce(sum(case when status = 'reserved' then reserved_tokens when status = 'succeeded' then total_tokens else 0 end), 0)
    into v_daily_used from public.generation_usage
    where user_id=p_user_id and provider=p_provider and created_at >= date_trunc('day', now());
  select coalesce(sum(case when status = 'reserved' then reserved_tokens when status = 'succeeded' then total_tokens else 0 end), 0)
    into v_monthly_used from public.generation_usage
    where user_id=p_user_id and provider=p_provider and billing_period_end=v_subscription.current_period_end;
  if v_daily_used + p_reserved_tokens > v_daily_limit then raise exception 'Daily token limit reached'; end if;
  if v_monthly_used + p_reserved_tokens > v_monthly_limit then raise exception 'Monthly token limit reached'; end if;
  insert into public.generation_usage(user_id, provider, model, status, reserved_tokens, billing_period_end)
    values(p_user_id, p_provider, p_model, 'reserved', p_reserved_tokens, v_subscription.current_period_end)
    returning id into usage_id;
  return next;
end; $$;

create or replace function public.complete_generation_quota(
  p_usage_id uuid, p_user_id uuid, p_prompt_tokens integer, p_completion_tokens integer, p_status text
) returns void language plpgsql security definer as $$
begin
  update public.generation_usage set
    prompt_tokens=greatest(p_prompt_tokens, 0), completion_tokens=greatest(p_completion_tokens, 0),
    total_tokens=greatest(p_prompt_tokens, 0)+greatest(p_completion_tokens, 0),
    status=p_status, completed_at=now()
  where id=p_usage_id and user_id=p_user_id and status='reserved';
  if not found then raise exception 'Usage reservation not found'; end if;
end; $$;
