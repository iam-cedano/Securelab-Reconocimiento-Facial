-- Queue state used by the ESP32 camera worker.
alter table public.reconocimientos_faciales
  add column if not exists capture_device_id text,
  add column if not exists capture_claimed_at timestamptz,
  add column if not exists capture_attempts integer not null default 0;

create index if not exists reconocimientos_faciales_pending_capture_idx
  on public.reconocimientos_faciales ("timestamp")
  where url_foto is null
    and resultado in ('captura_requerida', 'captura_en_progreso');

-- Service-role callers use this function to prevent two cameras from claiming
-- the same row. Stale claims become available again after two minutes.
create or replace function public.claim_pending_facial_capture(p_device_id text)
returns setof public.reconocimientos_faciales
language plpgsql
volatile
security invoker
set search_path = ''
as $$
begin
  if nullif(trim(p_device_id), '') is null then
    raise exception 'p_device_id is required';
  end if;

  return query
  with candidate as (
    select pending.id
    from public.reconocimientos_faciales as pending
    where pending.url_foto is null
      and (
        pending.resultado = 'captura_requerida'
        or (
          pending.resultado = 'captura_en_progreso'
          and pending.capture_claimed_at < now() - interval '2 minutes'
        )
      )
    order by pending."timestamp" asc
    for update skip locked
    limit 1
  )
  update public.reconocimientos_faciales as capture
  set resultado = 'captura_en_progreso',
      capture_device_id = p_device_id,
      capture_claimed_at = now(),
      capture_attempts = capture.capture_attempts + 1
  from candidate
  where capture.id = candidate.id
  returning capture.*;
end;
$$;

revoke all on function public.claim_pending_facial_capture(text) from public;
revoke all on function public.claim_pending_facial_capture(text) from anon;
revoke all on function public.claim_pending_facial_capture(text) from authenticated;
grant execute on function public.claim_pending_facial_capture(text) to service_role;

-- Facial images contain sensitive personal data, so downloads remain private.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'capturas-faciales',
  'capturas-faciales',
  false,
  1048576,
  array['image/jpeg']
)
on conflict (id) do update
set public = excluded.public,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;
