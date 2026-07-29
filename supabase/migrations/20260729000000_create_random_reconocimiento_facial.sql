-- Test helper: creates a motion event, then a pending facial-capture row
-- the ESP32 / simulator can claim.
create or replace function public.create_random_reconocimiento_facial()
returns public.reconocimientos_faciales
language plpgsql
volatile
security invoker
set search_path = ''
as $$
declare
  event_id uuid;
  inserted public.reconocimientos_faciales;
begin
  insert into public.eventos_movimiento (
    direccion,
    alerta_disparada
  )
  values (
    (array['entrada', 'salida'])[1 + floor(random() * 2)::int],
    true
  )
  returning id into event_id;

  insert into public.reconocimientos_faciales (
    evento_id,
    matricula_detectada,
    nivel_confianza,
    resultado,
    url_foto
  )
  values (
    event_id,
    null,
    null,
    'captura_requerida',
    null
  )
  returning * into inserted;

  return inserted;
end;
$$;

revoke all on function public.create_random_reconocimiento_facial() from public;
revoke all on function public.create_random_reconocimiento_facial() from anon;
grant execute on function public.create_random_reconocimiento_facial() to authenticated;
grant execute on function public.create_random_reconocimiento_facial() to service_role;
