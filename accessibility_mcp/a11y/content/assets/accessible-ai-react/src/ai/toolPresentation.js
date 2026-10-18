const WEB_OPERATIONS = new Set(["search_web", "web_search", "fetch_web", "web_navigation", "url_context"])
const COMMAND_OPERATIONS = new Set(["command", "execute_command", "terminal", "code_execution"])
const FILE_OPERATIONS = new Set(["file_edit", "edit_file", "write_file", "apply_patch"])

export function activityGroup(data = {}) {
  const operation = String(data.operation || data.name || "tool").toLowerCase()
  if (WEB_OPERATIONS.has(operation)) return "web_research"
  if (COMMAND_OPERATIONS.has(operation)) return "commands"
  if (FILE_OPERATIONS.has(operation)) return "files"
  if (operation === "context_compaction") return "context_compaction"
  if (operation === "connector") return `connector:${data.connector_name || data.display_name || "unknown"}`
  if (operation === "mcp") return `mcp:${data.server_name || "unknown"}:${data.display_name || "tool"}`
  return data.group_key || operation
}

export function runningText(data = {}) {
  const group = activityGroup(data)
  if (group === "web_research") return "Pesquisando na web..."
  if (group === "commands") return data.target_count > 1 ? "Executando comandos..." : "Executando comando..."
  if (group === "files") return data.target_count > 1 ? "Editando arquivos..." : "Editando arquivo..."
  if (group === "context_compaction") return "Compactando conversa..."
  if (group.startsWith("connector:")) return `Executando ${data.display_name || "conector"}...`
  if (group.startsWith("mcp:")) return `Executando ${data.display_name || "ferramenta"} no servidor MCP ${data.server_name || "configurado"}...`
  if (data.operation === "image_generation") return "Criando imagem..."
  if (data.operation === "image_description") return "Descrevendo imagem..."
  if (data.operation === "audio_listen") return "Ouvindo..."
  if (data.operation === "audio_transcription") return "Transcrevendo áudio..."
  return `Executando ${data.display_name || "ferramenta"}...`
}

export function completedText(activity) {
  const count = activity.affectedCount || 0
  if (activity.group === "web_research") {
    return count > 0
      ? `Executou pesquisa web; navegou em ${count} ${count === 1 ? "página" : "páginas"}.`
      : "Executou pesquisa web."
  }
  if (activity.group === "commands") return activity.executions > 1 ? "Executou comandos." : "Executou comando."
  if (activity.group === "files") return count > 1 ? "Editou arquivos." : "Editou um arquivo."
  if (activity.group === "context_compaction") {
    const saved = Number(activity.tokensSaved || 0)
    return saved > 0
      ? `Conversa compactada. Economizou cerca de ${saved} tokens.`
      : "Conversa compactada."
  }
  if (activity.group.startsWith("connector:")) {
    const suffix = count && activity.itemPlural
      ? `; ${activity.resultAction || "processou"} ${count} ${count === 1 ? activity.itemSingular : activity.itemPlural}`
      : ""
    return `Executou ${activity.displayName || "conector"}${suffix}.`
  }
  if (activity.group.startsWith("mcp:")) {
    return `Executou ${activity.displayName || "ferramenta"} no servidor MCP ${activity.serverName || "configurado"}.`
  }
  return `Executou ${activity.displayName || "ferramenta"}.`
}

export function isDirectMedia(operation) {
  return new Set(["image_generation", "image_description", "audio_listen", "audio_transcription"]).has(operation)
}
