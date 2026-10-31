import React, { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { ChatMessageView } from './components/ChatMessageView';
import { ChatInput } from './components/ChatInput';
import { ApplicationsDrawer } from './components/ApplicationsDrawer';
import type {
  ApplicationRecord,
  ApplicationStatus,
  ChatMessage,
  HealthStatus,
  JobListing,
  ResumeProfile,
} from './types';
import {
  applyToJob,
  checkHealth,
  getApplications,
  sendChatMessage,
  updateApplicationStatus,
  uploadResume,
} from './services/api';
import './App.css';

const INITIAL_WELCOME_MESSAGE: ChatMessage = {
  id: 'welcome_1',
  role: 'assistant',
  content: `Hello! I'm your AI Job Assistant.

I can help you find the right job opportunities and manage your job search.

**1. Resume Analysis**
Upload your PDF or DOCX resume to extract your skills, education, experience, and projects.

**2. Smart Job Recommendations**
Discover relevant opportunities from 1,700+ job listings based on your profile.

**3. Advanced Job Search**
Find jobs by role, skills, location, experience level, and remote preferences.

**4. Job Match Insights**
Understand why a particular job matches your skills and experience.

**5. Application Tracking**
Keep track of your selected job applications and check their status.

Let's get started! Upload your resume or ask me to find suitable jobs.`,
  timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
  suggested_prompts: [
    'Recommend jobs for me',
    'Show only remote developer jobs',
    'Show entry level Python jobs',
    'Find Java and Spring Boot jobs',
  ],
};

export const App: React.FC = () => {
  const [sessionId, setSessionId] = useState<string>(() => {
    const saved = localStorage.getItem('ai_job_session_id');
    if (saved) return saved;
    const newId = 'sess_' + Math.random().toString(36).substring(2, 10);
    localStorage.setItem('ai_job_session_id', newId);
    return newId;
  });

  const [activeTab, setActiveTab] = useState<'chat' | 'applications'>('chat');
  const [messages, setMessages] = useState<ChatMessage[]>([INITIAL_WELCOME_MESSAGE]);
  const [profile, setProfile] = useState<ResumeProfile | null>(() => {
    const saved = localStorage.getItem('ai_job_active_profile');
    return saved ? JSON.parse(saved) : null;
  });
  const [applications, setApplications] = useState<ApplicationRecord[]>([]);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isChatLoading, setIsChatLoading] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (activeTab === 'chat') {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isChatLoading, activeTab]);

  useEffect(() => {
    checkHealth()
      .then(setHealth)
      .catch((err) => console.warn('Health check failed:', err));

    getApplications(sessionId)
      .then(setApplications)
      .catch((err) => console.warn('Failed to load applications:', err));
  }, [sessionId]);

  useEffect(() => {
    if (profile) {
      localStorage.setItem('ai_job_active_profile', JSON.stringify(profile));
    } else {
      localStorage.removeItem('ai_job_active_profile');
    }
  }, [profile]);

  const handleSendMessage = async (userText: string) => {
    const nowTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const userMsg: ChatMessage = {
      id: 'msg_' + Date.now(),
      role: 'user',
      content: userText,
      timestamp: nowTime,
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsChatLoading(true);

    try {
      const response = await sendChatMessage(sessionId, userText, profile);

      const assistantMsg: ChatMessage = {
        id: 'msg_' + (Date.now() + 1),
        role: 'assistant',
        content: response.reply,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        jobs: response.jobs,
        application: response.application,
        applications: response.applications,
        suggested_prompts: response.suggested_prompts,
        action_type: response.action_type,
      };

      setMessages((prev) => [...prev, assistantMsg]);

      if (response.application || (response.applications && response.applications.length > 0)) {
        getApplications(sessionId).then(setApplications);
      }
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: 'err_' + Date.now(),
        role: 'assistant',
        content: `⚠️ **Connection Notice**: ${err.message || 'Unable to communicate with assistant backend.'}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        suggested_prompts: ['Try again', 'Show my applied jobs'],
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsChatLoading(false);
    }
  };

  const handleUploadResume = async (file: File) => {
    setIsUploading(true);
    try {
      const res = await uploadResume(file);
      setProfile(res.profile);

      const notifyMsg: ChatMessage = {
        id: 'upload_' + Date.now(),
        role: 'assistant',
        content: `📄 **Resume Uploaded & Parsed Successfully!**\n\n` +
          `• **Candidate**: **${res.profile.name}**\n` +
          `• **Target Designation**: **${res.profile.designation}**\n` +
          `• **Experience**: **${res.profile.experience_years.toFixed(1)} years**\n` +
          `• **Extracted Skills (${res.profile.skills.length})**: *${res.profile.skills.slice(0, 8).join(', ')}...*\n\n` +
          `I can now match your profile against 1,700+ real job listings. What would you like to search for?`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        suggested_prompts: [
          'Recommend the best jobs for my profile',
          'Show only remote jobs',
          'Show jobs requiring ' + (res.profile.skills[0] || 'Java'),
        ],
      };
      setMessages((prev) => [...prev, notifyMsg]);
    } catch (err: any) {
      alert(`Resume upload failed: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleClearProfile = () => {
    setProfile(null);
  };

  const handleApplyJob = async (job: JobListing) => {
    try {
      const created = await applyToJob(sessionId, job);
      setApplications((prev) => [created, ...prev]);

      const confirmationMsg: ChatMessage = {
        id: 'applied_' + Date.now(),
        role: 'assistant',
        content: `✅ **Application Tracked Successfully!**\n\n` +
          `• **Reference ID**: \`${created.application_id}\`\n` +
          `• **Position**: **${created.job_title}**\n` +
          `• **Company**: **${created.company}**\n` +
          `• **Status**: \`${created.status}\`\n\n` +
          `*(Please remember to complete your external submission on the official portal: [${created.company} Portal](${created.source_link}))*`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        suggested_prompts: ['Show my applied jobs', 'Recommend more jobs'],
      };
      setMessages((prev) => [...prev, confirmationMsg]);
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleUpdateStatus = async (appId: string, newStatus: ApplicationStatus) => {
    try {
      const updated = await updateApplicationStatus(appId, newStatus, sessionId);
      setApplications((prev) =>
        prev.map((a) => (a.application_id === appId ? updated : a))
      );
    } catch (err: any) {
      alert(`Status update failed: ${err.message}`);
    }
  };

  const handleNewChat = () => {
    const newId = 'sess_' + Math.random().toString(36).substring(2, 10);
    localStorage.setItem('ai_job_session_id', newId);
    setSessionId(newId);
    setMessages([INITIAL_WELCOME_MESSAGE]);
    setApplications([]);
  };

  const appliedJobIds = new Set(applications.map((a) => a.job_id));

  return (
    <div className="app-layout">
      <Header
        health={health}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        applicationsCount={applications.length}
        onNewChat={handleNewChat}
      />

      <div className="app-body">
        <Sidebar
          profile={profile}
          onUploadResume={handleUploadResume}
          onClearProfile={handleClearProfile}
          onSendQuickPrompt={handleSendMessage}
          isUploading={isUploading}
        />

        <main className="main-content">
          {activeTab === 'chat' ? (
            <div className="chat-container">
              <div className="messages-scroll-area">
                {messages.map((msg) => (
                  <ChatMessageView
                    key={msg.id}
                    message={msg}
                    onApplyJob={handleApplyJob}
                    onSelectPrompt={handleSendMessage}
                    appliedJobIds={appliedJobIds}
                  />
                ))}

                {isChatLoading && (
                  <div className="chat-message-row assistant-row loading-row">
                    <div className="avatar-wrap">
                      <div className="avatar assistant">🤖</div>
                    </div>
                    <div className="message-content-box">
                      <div className="message-bubble typing-bubble">
                        <span className="dot" />
                        <span className="dot" />
                        <span className="dot" />
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              <ChatInput
                onSendMessage={handleSendMessage}
                isLoading={isChatLoading}
              />
            </div>
          ) : (
            <ApplicationsDrawer
              applications={applications}
              onUpdateStatus={handleUpdateStatus}
            />
          )}
        </main>
      </div>
    </div>
  );
};

export default App;
