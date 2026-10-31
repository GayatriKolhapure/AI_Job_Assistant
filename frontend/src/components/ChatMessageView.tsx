import React from 'react';
import { Bot, Sparkles, User } from 'lucide-react';
import type { ChatMessage, JobListing } from '../types';
import { JobCard } from './JobCard';

interface ChatMessageViewProps {
  message: ChatMessage;
  onApplyJob: (job: JobListing) => Promise<void>;
  onSelectPrompt: (prompt: string) => void;
  appliedJobIds: Set<string>;
}

export const ChatMessageView: React.FC<ChatMessageViewProps> = ({
  message,
  onApplyJob,
  onSelectPrompt,
  appliedJobIds,
}) => {
  const isUser = message.role === 'user';

  const renderFormattedContent = (content: string) => {
    const lines = content.split('\n');
    return lines.map((line, idx) => {
      if (line.startsWith('### ')) {
        return <h4 key={idx} className="msg-h4">{line.replace('### ', '')}</h4>;
      }
      if (line.startsWith('## ')) {
        return <h3 key={idx} className="msg-h3">{line.replace('## ', '')}</h3>;
      }

      if (line.trim().startsWith('• ') || line.trim().startsWith('* ') || line.trim().startsWith('- ')) {
        const bulletText = line.trim().replace(/^[-*•]\s+/, '');
        return (
          <li key={idx} className="msg-li">
            {renderInlineMarkdown(bulletText)}
          </li>
        );
      }

      if (!line.trim()) {
        return <div key={idx} className="msg-spacing" />;
      }

      return (
        <p key={idx} className="msg-p">
          {renderInlineMarkdown(line)}
        </p>
      );
    });
  };

  const renderInlineMarkdown = (text: string) => {
    const parts = text.split(/(\*\*.*?\*\*|`.*?`|\[.*?\]\(.*?\))/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i}>{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith('`') && part.endsWith('`')) {
        return <code key={i} className="inline-code">{part.slice(1, -1)}</code>;
      }
      if (part.startsWith('[') && part.includes('](') && part.endsWith(')')) {
        const match = part.match(/\[(.*?)\]\((.*?)\)/);
        if (match) {
          return (
            <a key={i} href={match[2]} target="_blank" rel="noopener noreferrer" className="msg-link">
              {match[1]}
            </a>
          );
        }
      }
      return part;
    });
  };

  return (
    <div className={`chat-message-row ${isUser ? 'user-row' : 'assistant-row'}`}>
      <div className="avatar-wrap">
        {isUser ? (
          <div className="avatar user">
            <User size={16} />
          </div>
        ) : (
          <div className="avatar assistant">
            <Bot size={16} />
          </div>
        )}
      </div>

      <div className="message-content-box">
        <div className="message-header-meta">
          <span className="sender-name">{isUser ? 'You' : 'AI Assistant'}</span>
          <span className="timestamp">{message.timestamp}</span>
        </div>

        <div className="message-bubble">
          {renderFormattedContent(message.content)}
        </div>
        
        {message.jobs && message.jobs.length > 0 && (
          <div className="jobs-container-block">
            <div className="jobs-heading-row">
              <Sparkles size={16} className="sparkle-icon" />
              <span>Recommended Matches ({message.jobs.length} Positions)</span>
            </div>
            <div className="jobs-list">
              {message.jobs.map((matchRes, index) => (
                <JobCard
                  key={matchRes.job.job_id}
                  matchResult={matchRes}
                  index={index}
                  onApply={onApplyJob}
                  isApplied={appliedJobIds.has(matchRes.job.job_id)}
                />
              ))}
            </div>
          </div>
        )}

        {message.suggested_prompts && message.suggested_prompts.length > 0 && (
          <div className="prompt-pills-row">
            {message.suggested_prompts.map((prompt, idx) => (
              <button
                key={idx}
                className="prompt-pill"
                onClick={() => onSelectPrompt(prompt)}
              >
                {prompt}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
