import React, { useState } from 'react';
import { Briefcase, Building, Check, ExternalLink, Globe, MapPin, Send } from 'lucide-react';
import type { JobMatchResult } from '../types';

interface JobCardProps {
  matchResult: JobMatchResult;
  index: number;
  onApply: (job: JobMatchResult['job']) => Promise<void>;
  isApplied?: boolean;
}

export const JobCard: React.FC<JobCardProps> = ({
  matchResult,
  index,
  onApply,
  isApplied = false,
}) => {
  const { job, match_score, matching_skills, missing_skills, match_reason } = matchResult;
  const [applying, setApplying] = useState(false);
  const [appliedLocal, setAppliedLocal] = useState(isApplied);

  const handleApplyClick = async () => {
    if (appliedLocal || applying) return;
    setApplying(true);
    try {
      await onApply(job);
      setAppliedLocal(true);
    } finally {
      setApplying(false);
    }
  };

  const getScoreBadgeClass = (score: number) => {
    if (score >= 80) return 'score-high';
    if (score >= 60) return 'score-med';
    return 'score-low';
  };

  return (
    <div className="job-card">
      <div className="job-card-header">
        <div className="job-header-left">
          <span className="job-index-badge">#{index + 1}</span>
          <div>
            <h4 className="job-title">{job.title}</h4>
            <div className="job-company-row">
              <span className="job-company">
                <Building size={14} />
                {job.company}
              </span>
              <span className="job-location">
                <MapPin size={14} />
                {job.location}
              </span>
              <span className={`work-mode-pill ${job.work_mode.toLowerCase()}`}>
                {job.work_mode}
              </span>
            </div>
          </div>
        </div>

        <div className={`score-badge ${getScoreBadgeClass(match_score)}`}>
          <div className="score-number">{match_score}%</div>
          <div className="score-label">Match Score</div>
        </div>
      </div>

      <div className="job-match-reason">
        <strong>Why it matches:</strong> {match_reason}
      </div>

      <div className="job-metadata-row">
        <div className="meta-item">
          <Briefcase size={13} />
          <span>{job.experience_required}</span>
        </div>
        <div className="meta-item">
          <Globe size={13} />
          <span>Source: {job.source}</span>
        </div>
      </div>

      <div className="job-skills-section">
        {matching_skills && matching_skills.length > 0 && (
          <div className="skills-group">
            <span className="skills-heading">Matched Skills:</span>
            <div className="skills-pills">
              {matching_skills.map((s, idx) => (
                <span key={idx} className="skill-pill matched">
                  ✓ {s}
                </span>
              ))}
            </div>
          </div>
        )}

        {missing_skills && missing_skills.length > 0 && (
          <div className="skills-group">
            <span className="skills-heading">Desired Skills:</span>
            <div className="skills-pills">
              {missing_skills.map((s, idx) => (
                <span key={idx} className="skill-pill missing">
                  + {s}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="job-card-footer">
        <button
          className={`apply-btn ${appliedLocal ? 'applied' : ''}`}
          onClick={handleApplyClick}
          disabled={appliedLocal || applying}
        >
          {appliedLocal ? (
            <>
              <Check size={14} />
              Applied & Tracked
            </>
          ) : applying ? (
            <span>Saving Application...</span>
          ) : (
            <>
              <Send size={14} />
              Track Application
            </>
          )}
        </button>

        <a
          href={job.source_link}
          target="_blank"
          rel="noopener noreferrer"
          className="external-link-btn"
          title="Open official employer listing"
        >
          <ExternalLink size={14} />
          Official Apply Link
        </a>
      </div>
    </div>
  );
};
