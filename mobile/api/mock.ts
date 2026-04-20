import type { DashboardStats, Deadline, Reminder } from './types';

export const MOCK_STATS: DashboardStats = {
  total_deadlines: 12,
  pending_deadlines: 5,
  upcoming_reminders: 8,
  emails_processed_today: 23,
  connected_accounts: 2,
};

export const MOCK_DEADLINES: Deadline[] = [
  { id: 'dl-1', user_id: 'u1', title: 'Submit project proposal to client', due_at: new Date(Date.now() + 86400000).toISOString(), confidence_score: 0.95, source_text: 'From: manager@company.com', status: 'pending' },
  { id: 'dl-2', user_id: 'u1', title: 'Complete quarterly tax filing', due_at: new Date(Date.now() + 172800000).toISOString(), confidence_score: 0.88, source_text: 'From: accounting@firm.com', status: 'pending' },
  { id: 'dl-3', user_id: 'u1', title: 'Review pull request #247', due_at: new Date(Date.now() + 43200000).toISOString(), confidence_score: 0.92, source_text: 'From: dev-team@company.com', status: 'reminded' },
  { id: 'dl-4', user_id: 'u1', title: 'Renew cloud subscription', due_at: new Date(Date.now() + 604800000).toISOString(), confidence_score: 0.78, source_text: 'From: billing@cloud.io', status: 'pending' },
  { id: 'dl-5', user_id: 'u1', title: 'Send weekly status update', due_at: new Date(Date.now() + 7200000).toISOString(), confidence_score: 0.99, source_text: 'From: pm@company.com', status: 'pending' },
];

export const MOCK_REMINDERS: Reminder[] = [
  { id: 'rm-1', deadline_id: 'dl-1', user_id: 'u1', scheduled_at: new Date(Date.now() + 3600000).toISOString(), channel: 'email', status: 'pending', sent_at: null },
  { id: 'rm-2', deadline_id: 'dl-2', user_id: 'u1', scheduled_at: new Date(Date.now() + 7200000).toISOString(), channel: 'email', status: 'pending', sent_at: null },
  { id: 'rm-3', deadline_id: 'dl-3', user_id: 'u1', scheduled_at: new Date(Date.now() - 3600000).toISOString(), channel: 'email', status: 'sent', sent_at: new Date(Date.now() - 3500000).toISOString() },
  { id: 'rm-4', deadline_id: 'dl-4', user_id: 'u1', scheduled_at: new Date(Date.now() + 86400000).toISOString(), channel: 'push', status: 'pending', sent_at: null },
  { id: 'rm-5', deadline_id: 'dl-5', user_id: 'u1', scheduled_at: new Date(Date.now() - 7200000).toISOString(), channel: 'email', status: 'failed', sent_at: null },
  { id: 'rm-6', deadline_id: 'dl-1', user_id: 'u1', scheduled_at: new Date(Date.now() + 14400000).toISOString(), channel: 'sms', status: 'snoozed', sent_at: null },
];
