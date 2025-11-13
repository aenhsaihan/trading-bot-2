import { useState, useMemo } from 'react';
import { Notification, NotificationPriority } from '../types/notification';
import { NotificationCard } from './NotificationCard';
import { RefreshCw, Filter, ChevronRight } from 'lucide-react';

interface NotificationCenterProps {
  notifications: Notification[];
  onMarkRead: (id: string) => void;
  onRespond: (id: string, action: string) => void;
  onRefresh: () => void;
  onSelect?: (notification: Notification) => void;
  selectedNotificationId?: string;
  loading?: boolean;
  onCollapse?: () => void;
}

export function NotificationCenter({
  notifications,
  onMarkRead,
  onRespond,
  onRefresh,
  onSelect,
  selectedNotificationId,
  loading = false,
  onCollapse,
}: NotificationCenterProps) {
  const [showUnreadOnly, setShowUnreadOnly] = useState(false);
  const [priorityFilter, setPriorityFilter] = useState<NotificationPriority | 'all'>('all');

  const filteredNotifications = useMemo(() => {
    console.log('NotificationCenter: filtering notifications', {
      total: notifications.length,
      showUnreadOnly,
      priorityFilter,
    });
    let filtered = notifications.filter((n) => !n.responded);
    console.log('After filtering responded:', filtered.length);

    if (showUnreadOnly) {
      filtered = filtered.filter((n) => !n.read);
      console.log('After filtering unread:', filtered.length);
    }

    if (priorityFilter !== 'all') {
      filtered = filtered.filter((n) => n.priority === priorityFilter);
    }

    return filtered;
  }, [notifications, showUnreadOnly, priorityFilter]);

  const stats = useMemo(() => {
    const unread = notifications.filter((n) => !n.read).length;
    const critical = notifications.filter(
      (n) => n.priority === NotificationPriority.CRITICAL
    ).length;
    return { unread, critical, total: notifications.length };
  }, [notifications]);

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-[#0f0f1e] via-[#1a1a2e] to-[#0f0f1e]">
      {/* Header */}
      <div className="bg-dark-card/50 border-b border-gray-800 p-4 flex-shrink-0">
        <div className="flex items-center justify-between mb-1">
          <div>
            <h1 className="text-2xl font-bold text-white">🔔 Notifications</h1>
            <p className="text-sm text-gray-400">
              Always watching, always listening, always notifying
            </p>
          </div>
          {onCollapse && (
            <button
              onClick={onCollapse}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors text-gray-400 hover:text-white"
              title="Collapse notifications panel"
            >
              <ChevronRight size={20} />
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="bg-dark-card rounded-lg p-3 border border-gray-700">
            <div className="text-gray-400 text-xs mb-1">Total</div>
            <div className="text-xl font-bold text-white">{stats.total}</div>
          </div>
          <div className="bg-dark-card rounded-lg p-3 border border-gray-700">
            <div className="text-gray-400 text-xs mb-1">Unread</div>
            <div className="text-xl font-bold text-yellow-400">{stats.unread}</div>
          </div>
          <div className="bg-dark-card rounded-lg p-3 border border-gray-700">
            <div className="text-gray-400 text-xs mb-1">Critical</div>
            <div className="text-xl font-bold text-red-400">{stats.critical}</div>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-dark-card rounded-lg p-3 mb-4 flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <Filter size={18} className="text-gray-400" />
          <label className="flex items-center gap-2 text-sm text-gray-300">
            <input
              type="checkbox"
              checked={showUnreadOnly}
              onChange={(e) => setShowUnreadOnly(e.target.checked)}
              className="rounded"
            />
            Show unread only
          </label>
        </div>

        <select
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value as NotificationPriority | 'all')}
          className="bg-dark-bg border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
        >
          <option value="all">All Priorities</option>
          <option value={NotificationPriority.CRITICAL}>Critical</option>
          <option value={NotificationPriority.HIGH}>High</option>
          <option value={NotificationPriority.MEDIUM}>Medium</option>
          <option value={NotificationPriority.LOW}>Low</option>
          <option value={NotificationPriority.INFO}>Info</option>
        </select>

        <button
          onClick={onRefresh}
          disabled={loading}
          className="ml-auto flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium text-white transition-colors disabled:opacity-50"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

        {/* Notifications List */}
        {loading && filteredNotifications.length === 0 ? (
          <div className="text-center py-12 text-gray-400">Loading notifications...</div>
        ) : filteredNotifications.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-4xl mb-4">✨</div>
            <div className="text-gray-400 text-lg">
              No notifications - Everything is calm and monitored.
            </div>
          </div>
        ) : (
          <div>
            {filteredNotifications.map((notification) => (
              <NotificationCard
                key={notification.id}
                notification={notification}
                onMarkRead={onMarkRead}
                onRespond={onRespond}
                onSelect={onSelect}
                isSelected={notification.id === selectedNotificationId}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

