import React, { useState } from 'react';
import type { ApplicationRecord, ApplicationStatus } from '../types';
import { Briefcase, Building, Calendar, CheckCircle2, Clock, ExternalLink, MapPin } from 'lucide-react';

interface ApplicationsDrawerProps {
  applications: ApplicationRecord[];
  onUpdateStatus: (appId: string, newStatus: ApplicationStatus) => Promise<void>;
  onClose?: () => void;
}

const STATUS_OPTIONS: ApplicationStatus[] = [
  'Applied',
  'Under Review',
  'Interview',
  'Rejected',
  'Selected',
];

export const ApplicationsDrawer: React.FC<ApplicationsDrawerProps> = ({
  applications,
  onUpdateStatus,
}) => {
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const handleStatusChange = async (appId: string, newStatus: ApplicationStatus) => {
    setUpdatingId(appId);
    try {
      await onUpdateStatus(appId, newStatus);
    } finally {
      setUpdatingId(null);
    }
  };

  const getStatusBadgeClass = (status: ApplicationStatus) => {
    switch (status) {
      case 'Selected':
        return 'badge-selected';
      case 'Interview':
        return 'badge-interview';
      case 'Under Review':
        return 'badge-review';
      case 'Rejected':
        return 'badge-rejected';
      default:
        return 'badge-applied';
    }
  };

  if (applications.length === 0) {
    return (
      <div className="empty-apps-container">
        <div className="empty-icon-wrap">
          <Briefcase size={36} />
        </div>
        <h3>No Tracked Applications Yet</h3>
        <p>
          As you explore job recommendations in chat, click <strong>"Track Application"</strong> or type
          <em> "Apply to job 1"</em> to automatically save records into SQLite.
        </p>
      </div>
    );
  }

  return (
    <div className="apps-container">
      <div className="apps-header">
        <div>
          <h2>My Tracked Applications</h2>
          <p className="apps-subtitle">
            Persisted in SQLite database with duplicate submission prevention.
          </p>
        </div>
        <div className="apps-count-pill">
          <CheckCircle2 size={16} />
          <span>{applications.length} Recorded</span>
        </div>
      </div>

      <div className="apps-grid">
        {applications.map((app) => (
          <div key={app.application_id} className="app-card">
            <div className="app-card-top">
              <div>
                <span className="app-id-pill">{app.application_id}</span>
                <h3 className="app-title">{app.job_title}</h3>
                <div className="app-company">
                  <Building size={14} />
                  <span>{app.company}</span>
                </div>
              </div>

              <div className="status-selector-wrap">
                <span className={`status-pill ${getStatusBadgeClass(app.status)}`}>
                  {app.status}
                </span>
                <select
                  className="status-dropdown"
                  value={app.status}
                  disabled={updatingId === app.application_id}
                  onChange={(e) =>
                    handleStatusChange(app.application_id, e.target.value as ApplicationStatus)
                  }
                >
                  {STATUS_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="app-details-row">
              <div className="app-meta">
                <MapPin size={13} />
                <span>{app.location}</span>
              </div>
              <div className="app-meta">
                <Calendar size={13} />
                <span>Applied: {app.applied_date}</span>
              </div>
              <div className="app-meta">
                <Clock size={13} />
                <span>Updated: {new Date(app.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
              </div>
            </div>

            <div className="app-card-bottom">
              <span className="safe-notice">
                Official external submission required via employer portal
              </span>
              <a
                href={app.source_link}
                target="_blank"
                rel="noopener noreferrer"
                className="external-link-btn small"
              >
                <ExternalLink size={13} />
                Employer Portal
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
