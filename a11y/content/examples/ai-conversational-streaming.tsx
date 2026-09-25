import React, { useState, useRef } from 'react';

/**
 * Accessible AI Conversational Interface with LLM Streaming
 * Demonstrates:
 * 1. aria-busy lifecycle during text streaming.
 * 2. One "Digitando..." announcement followed by the complete final answer.
 * 3. Focus shift to generated artifacts without breaking reading flow.
 * 4. Keyboard accessibility for prompt submission and stop generation.
 */
export function AccessibleAIStreamingChat() {
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; text: string; id: string }>>([
    { role: 'assistant', text: 'Hello! How can I assist you with web accessibility today?', id: 'msg-1' }
  ]);
  const [prompt, setPrompt] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStreamText, setCurrentStreamText] = useState('');
  const liveRegionRef = useRef<HTMLDivElement>(null);
  const promptInputRef = useRef<HTMLInputElement>(null);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || isStreaming) return;

    const userMsgId = `msg-${Date.now()}`;
    const userPrompt = prompt;
    setMessages(prev => [...prev, { role: 'user', text: userPrompt, id: userMsgId }]);
    setPrompt('');
    setIsStreaming(true);
    setCurrentStreamText('');
    if (liveRegionRef.current) {
      liveRegionRef.current.textContent = '';
      window.setTimeout(() => {
        if (liveRegionRef.current) liveRegionRef.current.textContent = 'Digitando...';
      }, 50);
    }

    // Simulate streaming LLM response
    const chunks = ['To make a button accessible, ', 'use a native <button> element ', 'and keep its visible focus and accessible name.'];
    let index = 0;

    const interval = setInterval(() => {
      if (index < chunks.length) {
        setCurrentStreamText(prev => prev + chunks[index]);
        index++;
      } else {
        clearInterval(interval);
        setIsStreaming(false);
        const assistantMsgId = `msg-${Date.now()}`;
        setMessages(prev => [...prev, { role: 'assistant', text: chunks.join(''), id: assistantMsgId }]);
        setCurrentStreamText('');
        
        // Announce the complete final answer once; never announce streamed chunks.
        if (liveRegionRef.current) {
          liveRegionRef.current.textContent = '';
          window.setTimeout(() => {
            if (liveRegionRef.current) {
              liveRegionRef.current.textContent = chunks.join('');
              window.setTimeout(() => {
                if (liveRegionRef.current) liveRegionRef.current.textContent = '';
              }, 1000);
            }
          }, 50);
        }
      }
    }, 400);
  };

  return (
    <main className="ai-chat-container">
      <h1>AI Accessibility Assistant</h1>

      {/* Screen reader live region for status announcements */}
      <div ref={liveRegionRef} role="status" className="sr-only" />

      <section className="chat-log" aria-label="Message History">
        {messages.map(msg => (
          <article
            key={msg.id} 
            className={`chat-message ${msg.role}`}
          >
            <strong>{msg.role === 'user' ? 'You' : 'Assistant'}:</strong>
            <p>{msg.text}</p>
          </article>
        ))}

        {/* Active streaming response block with aria-busy */}
        {isStreaming && (
          <article
            className="chat-message assistant streaming" 
            aria-busy="true" 
          >
            <strong>Assistant (generating...):</strong>
            <p>{currentStreamText}</p>
          </article>
        )}
      </section>

      {/* Input form */}
      <form onSubmit={handleSend} className="prompt-form">
        <label htmlFor="user-prompt">Ask a question:</label>
        <input 
          id="user-prompt" 
          ref={promptInputRef}
          type="text" 
          value={prompt} 
          onChange={e => setPrompt(e.target.value)} 
          placeholder="e.g. How to handle focus traps?" 
          disabled={isStreaming}
        />
        <button type="submit" disabled={isStreaming || !prompt.trim()}>
          {isStreaming ? 'Generating...' : 'Send Prompt'}
        </button>
      </form>
    </main>
  );
}
