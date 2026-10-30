import React, { useRef, useState } from 'react';
import {
  Briefcase,
  Filter,
  RefreshCw,
  Sparkles,
  Upload,
  User,
  X,
} from 'lucide-react';
import type { ResumeProfile } from '../types';

interface SidebarProps {
  profile: ResumeProfile | null;
  onUploadResume: (file: File) => Promise<void>;
  onClearProfile: () => void;
  onSendQuickPrompt: (prompt: string) => void;
  isUploading: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  profile,
  onUploadResume,
  onClearProfile,
  onSendQuickPrompt,
  isUploading,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onUploadResume(e.target.files[0]);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onUploadResume(e.dataTransfer.files[0]);
    }
  };

  return (
    <aside className="sidebar">
      {/* 1. Resume Profile Section */}
      <div className="sidebar-section">
        <div className="section-header">
          <div className="section-title">
            <User size={16} />
            <span>Candidate Profile</span>
          </div>
          {profile && (
            <button className="text-btn" onClick={onClearProfile} title="Clear uploaded profile">
              <X size={14} /> Clear
            </button>
          )}
        </div>

        {profile ? (
          <div className="profile-card">
            <div className="profile-header">
              <div className="profile-avatar">
                {profile.name.charAt(0).toUpperCase()}
              </div>
              <div className="profile-info">
                <h4 className="profile-name">{profile.name}</h4>
                <div className="profile-desig">{profile.designation}</div>
              </div>
            </div>

            <div className="profile-meta-grid">
              <div className="meta-box">
                <span className="meta-label">Experience</span>
                <span className="meta-val">{profile.experience_years.toFixed(1)} yrs</span>
              </div>
              <div className="meta-box">
                <span className="meta-label">Skills Extracted</span>
                <span className="meta-val">{profile.skills.length} skills</span>
              </div>
            </div>

            <div className="profile-skills-list">
              <span className="skills-subheading">Key Tech Stack:</span>
              <div className="skills-tags">
                {profile.skills.slice(0, 8).map((skill, idx) => (
                  <span key={idx} className="profile-skill-tag">
                    {skill}
                  </span>
                ))}
                {profile.skills.length > 8 && (
                  <span className="profile-skill-tag more">
                    +{profile.skills.length - 8} more
                  </span>
                )}
              </div>
            </div>

            <button
              className="action-btn-primary full-width"
              onClick={() => onSendQuickPrompt('Recommend the top jobs for my resume profile')}
            >
              <Sparkles size={14} />
              Find Best Matches
            </button>
          </div>
        ) : (
          <div className="upload-container">
            <div
              className={`dropzone ${dragOver ? 'drag-over' : ''} ${isUploading ? 'loading' : ''}`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx"
                style={{ display: 'none' }}
                onChange={handleFileChange}
              />
              {isUploading ? (
                <div className="upload-status">
                  <RefreshCw className="spinner-icon" size={24} />
                  <span>Parsing resume with PyMuPDF...</span>
                </div>
              ) : (
                <>
                  <div className="upload-icon-circle">
                    <Upload size={20} />
                  </div>
                  <div className="upload-main-text">Upload Resume</div>
                  <div className="upload-sub-text">PDF or DOCX (Max 10MB)</div>
                </>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 2. Quick Filters */}
      <div className="sidebar-section">
        <div className="section-title">
          <Filter size={16} />
          <span>Quick Intent Queries</span>
        </div>

        <div className="filter-buttons">
          <button
            className="filter-pill-btn"
            onClick={() => onSendQuickPrompt('Show only remote software developer jobs')}
          >
            🌐 Only Remote Jobs
          </button>
          <button
            className="filter-pill-btn"
            onClick={() => onSendQuickPrompt('Show entry level and fresher developer jobs')}
          >
            🎓 Fresher / Entry Roles
          </button>
          <button
            className="filter-pill-btn"
            onClick={() => onSendQuickPrompt('Find Java and Spring Boot developer jobs')}
          >
            ☕ Java & Spring Boot
          </button>
          <button
            className="filter-pill-btn"
            onClick={() => onSendQuickPrompt('Find Python and AI engineer jobs')}
          >
            🐍 Python & AI / Data
          </button>
          <button
            className="filter-pill-btn"
            onClick={() => onSendQuickPrompt('Show my applied jobs')}
          >
            📋 View Applied Jobs
          </button>
        </div>
      </div>

      {/* 3. System Info Card */}
      <div className="sidebar-footer-card">
        <div className="footer-card-header">
          <Briefcase size={14} />
          <span>System Information</span>
        </div>
        <p className="footer-text">
          Features 1,790 verified real jobs with autonomous multi-agent routing and application tracking.
        </p>
      </div>
    </aside>
  );
};
