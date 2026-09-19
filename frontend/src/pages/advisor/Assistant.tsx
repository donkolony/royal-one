import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Skeleton, ErrorBanner } from '@/components/ui';
import ReactMarkdown from 'react-markdown';
import DOMPurify from 'dompurify';

export default function AdvisorAssistant() {
  const [question, setQuestion] = useState('');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<any[]>([]);

  const { data: documents } = useQuery({
    queryKey: ['documents'],
    queryFn: () => api.get('/documents'),
  });

  const askAssistant = useMutation({
    mutationFn: (q: string) => api.post('/assistant/query', { 
      query: q, 
      conversation_id: conversationId 
    }),
    onSuccess: (res: any) => {
      setConversationId(res.conversation_id);
      setMessages((prev) => [...prev, { role: 'assistant', data: res }]);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;
    setMessages((prev) => [...prev, { role: 'user', content: question }]);
    askAssistant.mutate(question);
    setQuestion('');
  };

  return (
    <div className="max-w-4xl mx-auto flex flex-col h-[calc(100vh-6rem)]">
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-slate-900">Document Assistant</h1>
        <div className="mt-2 bg-yellow-50 border-l-4 border-yellow-400 p-3 text-sm text-yellow-800">
          This assistant answers questions from approved documents only. Always verify with the source before advising a client. Not financial advice.
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-4 mb-4 p-4 bg-slate-50 rounded-lg border border-slate-200">
        {messages.length === 0 ? (
          <div className="text-center text-slate-500 mt-10">
            Ask a question about internal policies or document wording.
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] p-4 rounded-lg shadow-sm ${msg.role === 'user' ? 'bg-slate-800 text-white' : 'bg-white border border-slate-200 text-slate-800'}`}>
                {msg.role === 'user' ? (
                  <p>{msg.content}</p>
                ) : (
                  <div>
                    {!msg.data.grounded ? (
                      <div className="bg-amber-50 text-amber-800 p-3 rounded text-sm mb-2 border border-amber-200">
                        I couldn't find this in the approved documents. Try rephrasing, or check the document library.
                      </div>
                    ) : (
                      <div className="prose prose-sm prose-slate max-w-none">
                        <ReactMarkdown>{DOMPurify.sanitize(msg.data.answer)}</ReactMarkdown>
                      </div>
                    )}
                    
                    {msg.data.citations?.length > 0 && (
                      <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap gap-2">
                        {msg.data.citations.map((cite: any, idx: number) => (
                          <a 
                            key={idx} 
                            href={cite.url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 bg-slate-100 hover:bg-slate-200 text-xs text-slate-700 px-2 py-1 rounded"
                          >
                            [{idx + 1}] {cite.title} p.{cite.page}
                            {cite.is_synthetic && <span className="ml-1 text-[10px] bg-amber-100 text-amber-700 px-1 rounded">Demo</span>}
                          </a>
                        ))}
                      </div>
                    )}
                    {msg.data.latency_ms && (
                      <div className="mt-2 text-[10px] text-slate-400 text-right">
                        {msg.data.provider || 'AI'} • {msg.data.latency_ms}ms
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        
        {askAssistant.isPending && (
          <div className="flex justify-start">
            <div className="max-w-[80%] p-4 rounded-lg bg-white border border-slate-200 shadow-sm w-64">
              <Skeleton className="h-4 w-3/4 mb-2" />
              <Skeleton className="h-4 w-1/2" />
            </div>
          </div>
        )}
        {askAssistant.isError && (
          <div className="flex justify-start">
            <ErrorBanner error={askAssistant.error} />
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g., What is the excess for a hire car?"
          className="flex-1 rounded-md border-slate-300 shadow-sm focus:border-yellow-500 focus:ring-yellow-500 sm:text-sm min-h-[60px] resize-none p-3"
          rows={2}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
        />
        <button 
          type="submit" 
          disabled={askAssistant.isPending || !question.trim()}
          className="px-6 py-2 bg-slate-800 text-white font-medium rounded-md hover:bg-slate-700 disabled:opacity-50 h-[60px]"
        >
          Send
        </button>
      </form>
    </div>
  );
}
