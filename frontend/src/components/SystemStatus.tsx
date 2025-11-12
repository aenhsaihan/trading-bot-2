import { Activity, AlertTriangle, CheckCircle } from 'lucide-react';

interface SystemStatusProps {
  status: {
    status: string;
    message: string;
    unread_count: number;
    critical_count: number;
    high_count: number;
    total_notifications: number;
  };
}

export function SystemStatus({ status }: SystemStatusProps) {
  const getStatusColor = () => {
    switch (status.status) {
      case 'critical':
        return 'border-red-500 bg-red-500/10';
      case 'attention':
        return 'border-orange-500 bg-orange-500/10';
      case 'active':
        return 'border-blue-500 bg-blue-500/10';
      default:
        return 'border-green-500 bg-green-500/10';
    }
  };

  const getStatusIcon = () => {
    switch (status.status) {
      case 'critical':
        return <AlertTriangle className="text-red-500" size={24} />;
      case 'attention':
        return <Activity className="text-orange-500" size={24} />;
      default:
        return <CheckCircle className="text-green-500" size={24} />;
    }
  };

  return (
    <div
      className={`border-2 rounded-xl p-6 mb-6 text-center ${getStatusColor()}`}
    >
      <div className="flex items-center justify-center gap-3 mb-2">
        {getStatusIcon()}
        <div className="text-xl font-semibold text-white">{status.message}</div>
      </div>
      <div className="text-sm text-gray-400">
        Monitoring {status.total_notifications} signals • Always watching, always listening
      </div>
    </div>
  );
}

