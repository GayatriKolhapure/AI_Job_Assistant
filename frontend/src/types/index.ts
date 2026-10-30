export interface ExperienceDetail {
  role: string;
  company: string;
  duration: string;
  description: string;
}

export interface EducationDetail {
  institution: string;
  degree: string;
  field_of_study: string;
  year?: string;
}

export interface ProjectDetail {
  title: string;
  description: string;
  technologies: string[];
}

export interface ResumeProfile {
  name: string;
  email: string;
  phone: string;
  designation: string;
  skills: string[];
  experience_years: number;
  experience_details?: ExperienceDetail[];
  education?: EducationDetail[];
  projects?: ProjectDetail[];
  certifications?: string[];
}

export interface JobListing {
  job_id: string;
  title: string;
  company: string;
  location: string;
  work_mode: string;
  experience_required: string;
  min_experience_years: number;
  skills: string[];
  description: string;
  source: string;
  source_link: string;
  posted_date?: string;
}

export interface JobMatchResult {
  job: JobListing;
  match_score: number;
  matching_skills: string[];
  missing_skills: string[];
  experience_fit: string;
  match_reason: string;
}

export type ApplicationStatus = 'Applied' | 'Under Review' | 'Interview' | 'Rejected' | 'Selected';

export interface ApplicationRecord {
  application_id: string;
  session_id: string;
  job_id: string;
  job_title: string;
  company: string;
  location: string;
  source_link: string;
  status: ApplicationStatus;
  applied_date: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  jobs?: JobMatchResult[];
  application?: ApplicationRecord;
  applications?: ApplicationRecord[];
  suggested_prompts?: string[];
  action_type?: string;
}

export interface ChatResponse {
  session_id: string;
  reply: string;
  action_type: string;
  jobs: JobMatchResult[];
  application?: ApplicationRecord;
  applications: ApplicationRecord[];
  suggested_prompts: string[];
  timestamp: string;
  is_mock: boolean;
}

export interface HealthStatus {
  status: string;
  app_name: string;
  environment: string;
  mock_mode: boolean;
  version: string;
  timestamp: string;
}

