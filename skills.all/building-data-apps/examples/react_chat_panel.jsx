// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import React, { useState, useRef, useEffect, Component } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Send, Bot, User, Loader2, BrainCircuit, ChevronDown, ChevronRight, X } from 'lucide-react';

// Required component to catch ReactMarkdown v10+ crash parsing errors
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  render() {
    if (this.state.hasError) {
      return <div className="text-red-500 text-xs p-2">MD Err: {this.state.error.message}</div>;
    }
    return this.props.children;
  }
}

export default function ChatPanel({ isOpen, onClose, contextText }) {
  const [messages, setMessages] = useState([
    { role: 'model', content: "Hi! Ask me any questions about the data." }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [expandedThoughts, setExpandedThoughts] = useState({});
  const bottomRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = Math.min(scrollHeight, 112) + 'px';
      textareaRef.current.style.overflowY = scrollHeight > 112 ? 'auto' : 'hidden';
    }
  }, [input]);

  const toggleThought = (idx) => {
    setExpandedThoughts(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend(e);
    }
  };

  const handleSend = async (e, overrideText = null) => {
    e?.preventDefault();
    const textToSend = overrideText || input;
    if (!textToSend.trim() || isLoading) return;

    if (!overrideText) setInput('');
    setIsLoading(true);

    const currentMessages = [...messages, { role: 'user', content: textToSend.trim() }];

    // Add empty placeholder model message
    const nextIdx = currentMessages.length;
    let thinking = '';
    let reply = '';
    let suggestions = [];

    setMessages([...currentMessages, { role: 'model', content: '', thoughts: '', suggestions: [] }]);

    try {
      // Use Fetch API for Server-Sent Events (SSE) streaming!
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: contextText ? `[Context: ${contextText}] ${textToSend.trim()}` : textToSend.trim(),
          history: currentMessages.slice(0, -1)
        })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        setIsLoading(false); // Hide global loader
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep incomplete fragments

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.replace('data: ', '').trim();
            if (dataStr === '[DONE]') break;
            if (dataStr) {
              try {
                const parsed = JSON.parse(dataStr);
                if (parsed.type === 'THOUGHT') {
                  thinking += parsed.content + '\n';
                } else if (parsed.type === 'SUGGESTION') {
                  suggestions.push(parsed.content);
                } else {
                  reply += parsed.content;
                }

                setMessages(prev => {
                  const updated = [...prev];
                  updated[nextIdx] = {
                    role: 'model',
                    content: reply,
                    thoughts: thinking,
                    suggestions: suggestions
                  };
                  return updated;
                });
              } catch (e) {
                console.error('JSON parse fail:', dataStr);
              }
            }
          }
        }
      }
    } catch (error) {
      console.error(error);
      setMessages([...currentMessages, { role: 'model', content: `⚠️ Error connecting to server.` }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={`fixed top-0 right-0 h-full w-[400px] bg-white dark:bg-[#1a1a1a] shadow-2xl flex flex-col transition-transform ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}>
      <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-800">
        <div className="font-semibold text-slate-900 dark:text-white">Chat</div>
        <button onClick={onClose}><X className="w-5 h-5 text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200" /></button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-800 flex items-center justify-center">
              <Bot className="w-4 h-4 text-slate-500 dark:text-slate-300" />
            </div>
            <div className="max-w-[85%] flex flex-col gap-2">

              {/* 1. Thoughts Box (Collapsible) */}
              {m.role === 'model' && m.thoughts && m.thoughts.trim().length > 0 && (
                <div className="bg-slate-50 dark:bg-[#1e1e1e] border border-slate-200 dark:border-slate-700/60 rounded-xl overflow-hidden shadow-sm">
                  <button
                    onClick={() => toggleThought(i)}
                    className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/50"
                  >
                    {expandedThoughts[i] ? <ChevronDown className="w-3.5 h-3.5 flex-shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 flex-shrink-0" />}
                    <BrainCircuit className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
                    {/* Dynamic Title Tracking */}
                    <span className="truncate text-left">
                      {(() => {
                        if (m.content && m.content.length > 0) return "View reasoning process";
                        const lines = m.thoughts.split('\n').filter(l => l.trim().length > 0);
                        return lines.length > 0 ? lines[lines.length - 1] : "Analyzing context...";
                      })()}
                    </span>
                  </button>
                  {/* Broken up string mapping instead of Markdown to parse explicit single newline logs */}
                  {expandedThoughts[i] && (
                    <div className="px-3 pb-3 pt-3 border-t border-slate-200 dark:border-slate-800/50 max-h-[250px] overflow-y-auto bg-slate-100 dark:bg-black/20 text-[11px] font-mono leading-relaxed text-slate-600 dark:text-slate-400 flex flex-col gap-2">
                      {m.thoughts.split('\n').filter(l => l.trim().length > 0).map((line, idx) => (
                        <div key={idx} className="flex gap-2 items-start">
                          <div className="text-slate-400 dark:text-slate-600 mt-[2px]">›</div>
                          <div className="break-words whitespace-pre-wrap">{line}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* 2. Loading Pulse (Wait State) */}
              {m.role === 'model' && !m.content && !expandedThoughts[i] && (
                <div className="flex items-center gap-2 text-xs text-slate-500 italic ml-1 mb-1 p-1">
                  <Loader2 className="w-3 h-3 animate-spin" /> {m.thoughts ? 'Thinking...' : 'Gathering insights...'}
                </div>
              )}

              {/* 3. FINAL_RESPONSE Rendering (Markdown) */}
              {m.content && (
                <div className={`p-3 rounded-2xl text-sm leading-relaxed ${m.role === 'user' ? 'bg-blue-600 text-white rounded-tr-none' : 'bg-slate-100 dark:bg-[#262626] text-slate-800 dark:text-slate-200 rounded-tl-none border border-slate-200 dark:border-slate-700/50 shadow-sm'}`}>
                  {m.role === 'model' ? (
                    <ErrorBoundary>
                      {/* MUST place className on the parent div, DO NOT pass to ReactMarkdown explicitly for v10+ compatibility */}
                      <div className="[&>p]:mb-2 [&>p:last-child]:mb-0 [&>ul]:list-disc [&>ul]:ml-5 [&>h3]:font-semibold [&>h3]:text-slate-800 dark:[&>h3]:text-slate-100 [&>h3]:mb-1 [&>h3]:mt-3 [&>ol]:list-decimal [&>ol]:ml-5 [&_code]:bg-black/5 dark:[&_code]:bg-black/30 [&_code]:px-1.5 [&_code]:rounded">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {m.content}
                        </ReactMarkdown>
                      </div>
                    </ErrorBoundary>
                  ) : (
                    <div className="whitespace-pre-wrap">{m.content}</div>
                  )}
                </div>
              )}

              {/* 4. Smart Suggestions Rendering */}
              {m.role === 'model' && m.suggestions && m.suggestions.length > 0 && (
                <div className="flex flex-col gap-1.5 mt-2">
                  {m.suggestions.slice(0, 3).map((s, idx) => (
                    <button
                      key={idx} onClick={() => handleSend(null, s)} disabled={isLoading}
                      className="text-left text-xs bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-800/40 text-blue-700 dark:text-blue-300 p-2 rounded-lg border border-blue-200 dark:border-blue-800/30 transition-colors"
                    >{s}</button>
                  ))}
                </div>
              )}

            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSend} className="p-4 border-t border-slate-200 dark:border-slate-800 flex items-end bg-slate-100 dark:bg-[#121212] relative">
        <textarea
          ref={textareaRef}
          value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown} disabled={isLoading}
          placeholder="Ask a question..."
          rows={1}
          className="w-full bg-white dark:bg-[#1a1a1a] border border-slate-300 dark:border-slate-700 rounded-xl pl-4 pr-12 py-3 text-sm focus:outline-none focus:border-blue-500 text-slate-800 dark:text-slate-100 placeholder-slate-500 dark:placeholder-slate-400 resize-none overscroll-contain"
        />
        <button type="submit" disabled={!input.trim() || isLoading} className="absolute right-6 bottom-6 p-2 bg-blue-600 hover:bg-blue-700 rounded-full text-white transition-colors disabled:opacity-50">
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}
