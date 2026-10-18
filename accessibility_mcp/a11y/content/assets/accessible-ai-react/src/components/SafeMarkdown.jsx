import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

export function SafeMarkdown({ children }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      skipHtml
      components={{
        hr: () => null,
        a: ({ children: label, ...props }) => <a {...props}>{label}</a>,
        table: props => <div className="table-scroll" tabIndex="0"><table {...props} /></div>,
      }}
    >{children}</ReactMarkdown>
  )
}

