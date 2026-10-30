import React from 'react';
import { Bot, CheckCircle2, History, MessageSquarePlus, Sparkles } from 'lucide-react';
import type { HealthStatus } from '../types';

interface HeaderProps {
  health: HealthStatus | null;
  activeTab: 'chat' | 'applications';
  setActiveTab: (tab: 'chat' | 'applications') => void;
  applicationsCount: number;
  onNewChat: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  health,
  activeTab,
  setActiveTab,
  applicationsCount,
  onNewChat,
}) => {
  return (
    <header className="header">
      <div className="header-left">
        <div className="logo-badge">
          <Bot className="logo-icon" size={24} />
        </div>
        <div>
          <div className="brand-title">
            <span>AI</span> Job Assistant
          </div>
          <div className="brand-subtitle">
            Autonomous multi-agent job matcher & application tracker • 1,700+ real listings
          </div>
        </div>
      </div>

      <div className="header-center">
        <button
          className={`tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => setActiveTab('chat')}
        >
          <Sparkles size={16} />
          Conversational Assistant
        </button>
        <button
          className={`tab-btn ${activeTab === 'applications' ? 'active' : ''}`}
          onClick={() => setActiveTab('applications')}
        >
          <History size={16} />
          Applications
          {applicationsCount > 0 && <span className="tab-count">{applicationsCount}</span>}
        </button>
      </div>

      <div className="header-right">
        {health && (
          <div className="health-pill" title="Backend API status">
            <CheckCircle2 size={14} className="online-icon" />
            <span>Online</span>
            {health.mock_mode && <span className="mock-badge">Mock LLM Mode</span>}
          </div>
        )}
        <button className="new-chat-btn" onClick={onNewChat} title="Start new conversation">
          <MessageSquarePlus size={16} />
          <span>New Chat</span>
        </button>
      </div>
    </header>
  );
};
