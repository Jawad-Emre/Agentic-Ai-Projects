create table if not exists public.agent_memory (
    sender text primary key,
    labels jsonb not null default '[]'::jsonb,
    importance_score double precision not null default 0,
    last_action text not null,
    last_success boolean not null default false,
    updated_at timestamptz not null default now()
);

create or replace function public.touch_agent_memory_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists agent_memory_updated_at on public.agent_memory;
create trigger agent_memory_updated_at
before update on public.agent_memory
for each row execute function public.touch_agent_memory_updated_at();