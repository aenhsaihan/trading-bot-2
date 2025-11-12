import { Notification } from '../types/notification';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export class NotificationAPI {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  async getNotifications(limit?: number, unreadOnly: boolean = false): Promise<{
    notifications: Notification[];
    total: number;
    unread_count: number;
  }> {
    const params = new URLSearchParams();
    if (limit) params.append('limit', limit.toString());
    if (unreadOnly) params.append('unread_only', 'true');

    const response = await fetch(`${this.baseUrl}/notifications?${params}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch notifications: ${response.statusText}`);
    }
    return response.json();
  }

  async getNotification(id: string): Promise<Notification> {
    const response = await fetch(`${this.baseUrl}/notifications/${id}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch notification: ${response.statusText}`);
    }
    return response.json();
  }

  async createNotification(data: {
    type: string;
    priority: string;
    title: string;
    message: string;
    source: string;
    symbol?: string;
    confidence_score?: number;
    urgency_score?: number;
    promise_score?: number;
    metadata?: Record<string, any>;
    actions?: string[];
  }): Promise<Notification> {
    const response = await fetch(`${this.baseUrl}/notifications`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new Error(`Failed to create notification: ${response.statusText}`);
    }
    return response.json();
  }

  async markAsRead(id: string): Promise<Notification> {
    const response = await fetch(`${this.baseUrl}/notifications/${id}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ read: true }),
    });
    if (!response.ok) {
      throw new Error(`Failed to mark as read: ${response.statusText}`);
    }
    return response.json();
  }

  async respondToNotification(
    id: string,
    action: string,
    customMessage?: string
  ): Promise<Notification> {
    const params = new URLSearchParams({ action });
    if (customMessage) params.append('custom_message', customMessage);

    const response = await fetch(
      `${this.baseUrl}/notifications/${id}/respond?${params}`,
      {
        method: 'POST',
      }
    );
    if (!response.ok) {
      throw new Error(`Failed to respond: ${response.statusText}`);
    }
    return response.json();
  }

  async deleteNotification(id: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/notifications/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error(`Failed to delete notification: ${response.statusText}`);
    }
  }

  async getStats(): Promise<Record<string, any>> {
    const response = await fetch(`${this.baseUrl}/notifications/stats/summary`);
    if (!response.ok) {
      throw new Error(`Failed to fetch stats: ${response.statusText}`);
    }
    return response.json();
  }

  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/health`);
      return response.ok;
    } catch {
      return false;
    }
  }
}

export const notificationAPI = new NotificationAPI();

