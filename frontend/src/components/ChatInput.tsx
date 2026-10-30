import React, { useState, useRef } from 'react';
import { Send, CornerDownLeft } from 'lucide-react';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  isLoading: boolean;
  disabled?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  isLoading,
  disabled = false,
}) => {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!text.trim() || isLoading || disabled) return;
    onSendMessage(text.trim());
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    // Auto-adjust height
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
  };

  return (
    <div className="chat-input-wrapper">
      <form onSubmit={handleSubmit} className="chat-input-form">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Ask for job recommendations, filter by remote/skills, or say 'Apply to job 1'..."
          disabled={disabled || isLoading}
          rows={1}
          className="chat-textarea"
        />

        <div className="input-actions-bar">
          <span className="input-hint">
            <CornerDownLeft size={12} /> Enter to send • Shift+Enter for new line
          </span>
          <button
            type="submit"
            className="send-message-btn"
            disabled={!text.trim() || isLoading || disabled}
          >
            {isLoading ? (
              <span className="spinner-dots">•••</span>
            ) : (
              <>
                <Send size={15} />
                <span>Send</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
