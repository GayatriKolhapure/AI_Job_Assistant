import type {
  ApplicationRecord,
  ChatResponse,
  HealthStatus,
  JobListing,
  ResumeProfile,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export async function checkHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE_URL}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return res.json();
}

export async function uploadResume(file: File): Promise<{
  success: boolean;
  filename: string;
  profile: ResumeProfile;
  text_preview: string;
  message: string;
}> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE_URL}/api/resume/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to upload and parse resume');
  }

  return res.json();
}

export async function sendChatMessage(
  sessionId: string,
  message: string,
  resumeProfile?: ResumeProfile | null
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      message,
      resume_profile: resumeProfile || null,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to process chat message');
  }

  return res.json();
}

export async function getApplications(sessionId: string): Promise<ApplicationRecord[]> {
  const res = await fetch(`${API_BASE_URL}/api/applications?session_id=${encodeURIComponent(sessionId)}`);
  if (!res.ok) throw new Error('Failed to fetch applications');
  const data = await res.json();
  return data.applications || [];
}

export async function applyToJob(
  sessionId: string,
  job: JobListing
): Promise<ApplicationRecord> {
  const res = await fetch(`${API_BASE_URL}/api/applications`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      job_id: job.job_id,
      job_title: job.title,
      company: job.company,
      location: job.location,
      source_link: job.source_link,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to record application');
  }

  return res.json();
}

export async function updateApplicationStatus(
  applicationId: string,
  newStatus: string,
  sessionId: string
): Promise<ApplicationRecord> {
  const res = await fetch(`${API_BASE_URL}/api/applications/${applicationId}/status?session_id=${encodeURIComponent(sessionId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: newStatus }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to update application status');
  }

  return res.json();
}
