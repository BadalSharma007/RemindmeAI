export interface DashboardStats {
  total_deadlines: number;
  pending_deadlines: number;
  upcoming_reminders: number;
  emails_processed_today: number;
  connected_accounts: number;
}

export interface Deadline {
  id: string;
  user_id: string;
  title: string;
  due_at: string;
  confidence_score: number;
  source_text: string | null;
  status: 'pending' | 'reminded' | 'completed' | 'dismissed';
}

export interface Reminder {
  id: string;
  deadline_id: string;
  user_id: string;
  scheduled_at: string;
  channel: string;
  status: 'pending' | 'sent' | 'failed' | 'snoozed';
  sent_at: string | null;
}

export interface UserProfile {
  id: string;
  email: string;
  display_name: string | null;
  timezone: string;
}
