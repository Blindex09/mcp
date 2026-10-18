export async function streamPost(url, body, onEvent, signal) {
  const response = await fetch(url, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body), signal,
  })
  if (!response.ok || !response.body) throw new Error(`HTTP ${response.status}`)
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  let terminal = false

  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
    const frames = buffer.split(/\r?\n\r?\n/)
    buffer = frames.pop() || ""
    for (const frame of frames) {
      const data = frame.split(/\r?\n/)
        .filter(line => line.startsWith("data:"))
        .map(line => line.slice(5).trimStart()).join("\n")
      if (!data) continue
      const event = JSON.parse(data)
      onEvent(event)
      if (["turn.completed", "turn.failed", "turn.cancelled"].includes(event.type)) terminal = true
    }
    if (done) break
  }
  if (!terminal) throw new Error("O fluxo terminou sem evento terminal")
}

