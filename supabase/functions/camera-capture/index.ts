import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const BUCKET = 'capturas-faciales'
const MAX_IMAGE_BYTES = 1024 * 1024
const jsonHeaders = { 'Content-Type': 'application/json' }

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: jsonHeaders })
}

function secretKey(): string {
  const standard = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')
  if (standard) return standard

  // Newer projects can expose secret keys as a JSON map.
  const secretKeys = JSON.parse(Deno.env.get('SUPABASE_SECRET_KEYS') ?? '{}')
  const key = secretKeys.default
  if (!key) throw new Error('No Supabase service-role secret is configured')
  return key
}

function validDevice(req: Request): string | null {
  const expected = Deno.env.get('DEVICE_API_TOKEN')
  const provided = req.headers.get('x-device-token')
  const deviceId = req.headers.get('x-device-id')

  if (!expected || !provided || provided.length !== expected.length) return null

  let difference = 0
  for (let index = 0; index < expected.length; index++) {
    difference |= expected.charCodeAt(index) ^ provided.charCodeAt(index)
  }
  if (difference !== 0) return null
  if (!deviceId || !/^[a-zA-Z0-9_-]{1,64}$/.test(deviceId)) return null
  return deviceId
}

Deno.serve(async (req) => {
  try {
    const deviceId = validDevice(req)
    if (!deviceId) return json({ error: 'unauthorized device' }, 401)

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      secretKey(),
      { auth: { persistSession: false, autoRefreshToken: false } },
    )

    if (req.method === 'GET') {
      const { data, error } = await supabase.rpc(
        'claim_pending_facial_capture',
        { p_device_id: deviceId },
      )
      if (error) throw error
      if (!data?.length) return new Response(null, { status: 204 })

      const capture = data[0]
      return json({
        id: capture.id,
        evento_id: capture.evento_id,
        timestamp: capture.timestamp,
      })
    }

    if (req.method !== 'POST') {
      return json({ error: 'method not allowed' }, 405)
    }

    const captureId = req.headers.get('x-capture-id')
    if (!captureId || !/^[0-9a-f-]{36}$/i.test(captureId)) {
      return json({ error: 'invalid x-capture-id' }, 400)
    }

    const declaredLength = Number(req.headers.get('content-length') ?? 0)
    if (declaredLength < 4 || declaredLength > MAX_IMAGE_BYTES) {
      return json({ error: 'JPEG must be between 4 bytes and 1 MiB' }, 413)
    }

    const image = new Uint8Array(await req.arrayBuffer())
    if (
      image.length !== declaredLength ||
      image.length > MAX_IMAGE_BYTES ||
      image[0] !== 0xff ||
      image[1] !== 0xd8 ||
      image[image.length - 2] !== 0xff ||
      image[image.length - 1] !== 0xd9
    ) {
      return json({ error: 'body is not a complete JPEG image' }, 400)
    }

    const objectPath = `${captureId}/${crypto.randomUUID()}.jpg`
    const { error: uploadError } = await supabase.storage
      .from(BUCKET)
      .upload(objectPath, image, {
        contentType: 'image/jpeg',
        upsert: false,
      })
    if (uploadError) throw uploadError

    const storedPath = `${BUCKET}/${objectPath}`
    const { data: updated, error: updateError } = await supabase
      .from('reconocimientos_faciales')
      .update({
        url_foto: storedPath,
        resultado: 'captura_completada',
      })
      .eq('id', captureId)
      .eq('capture_device_id', deviceId)
      .eq('resultado', 'captura_en_progreso')
      .select('id')
      .maybeSingle()

    if (updateError || !updated) {
      await supabase.storage.from(BUCKET).remove([objectPath])
      if (updateError) throw updateError
      return json({ error: 'capture is not claimed by this device' }, 409)
    }

    return json({ id: captureId, object_path: storedPath })
  } catch (error) {
    console.error(error)
    return json({ error: 'camera capture request failed' }, 500)
  }
})
