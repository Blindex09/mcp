import { SafeMarkdown } from "./SafeMarkdown.jsx"

function formatDuration(milliseconds) {
  return `${Math.max(0, Math.round(milliseconds / 1000))}s`
}

export function Turn({ turn, now }) {
  const duration = turn.isBusy ? now - turn.startedAt : turn.elapsedMs
  return (
    <section className="turn" aria-busy={turn.isBusy ? "true" : "false"}>
      <article className="message user-message">
        <p className="author">Você</p>
        <p>{turn.userText}</p>
      </article>

      {turn.reasoningText && (
        <details>
          <summary>Pensamento da IA</summary>
          <p>{turn.reasoningText}</p>
        </details>
      )}

      {turn.activityOrder.map(key => {
        const activity = turn.activities[key]
        if (!activity) return null
        return (
          <div className={`activity activity-${activity.status}`} key={key}>
            <p>{activity.text}</p>
            {activity.status === "running" && activity.progress.map((line, index) => <p key={index}>{line}</p>)}
          </div>
        )
      })}

      <article className="message assistant-message">
        <p className="author">IA assistente</p>
        {turn.answerIsPartial && <p>Resposta parcial.</p>}
        <div className="answer-stream"><SafeMarkdown>{turn.answerText}</SafeMarkdown></div>
        {turn.error && <p className="error">{turn.error}</p>}
      </article>

      {turn.media.map((media, index) => (
        <div key={index}>
          {media.operation === "image_generation" && <img src={media.url} alt={media.alt || "Imagem gerada pela IA"} />}
          {media.operation === "image_description" && <p>{media.text}</p>}
          {media.operation === "audio_transcription" && <p>{media.text}</p>}
          {media.operation === "audio_listen" && <audio controls src={media.url} />}
        </div>
      ))}

      {Object.keys(turn.sources).length > 0 && (
        <section aria-labelledby={`sources-${turn.id}`}>
          <h2 id={`sources-${turn.id}`}>Fontes consultadas</h2>
          <ul>{Object.values(turn.sources).map(source => (
            <li key={source.url}><a href={source.url}>{source.title || new URL(source.url).hostname}</a></li>
          ))}</ul>
        </section>
      )}

      <p className="turn-duration">
        {turn.isBusy ? `Processando há ${formatDuration(duration)}` : `Processou em ${formatDuration(duration)}`}
      </p>
    </section>
  )
}
