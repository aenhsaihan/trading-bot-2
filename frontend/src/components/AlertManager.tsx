import { useState, useEffect } from "react";
import {
  Bell,
  Plus,
  Edit,
  Trash2,
  ToggleLeft,
  ToggleRight,
  AlertCircle,
  CheckCircle,
} from "lucide-react";
import { Alert, AlertCreate } from "../types/alert";
import { alertAPI } from "../services/api";

interface AlertManagerProps {
  symbol?: string; // Optional symbol filter
  onAlertCreated?: () => void;
}

export function AlertManager({ symbol, onAlertCreated }: AlertManagerProps) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingAlert, setEditingAlert] = useState<Alert | null>(null);
  const [formData, setFormData] = useState<AlertCreate>({
    symbol: symbol || "BTC/USDT",
    alert_type: "price",
    enabled: true,
  });

  // Popular trading pairs
  const tradingPairs = [
    "BTC/USDT",
    "ETH/USDT",
    "BNB/USDT",
    "SOL/USDT",
    "DOGE/USDT",
    "ADA/USDT",
    "MATIC/USDT",
    "AVAX/USDT",
    "XRP/USDT",
    "DOT/USDT",
    "LINK/USDT",
    "UNI/USDT",
  ];

  const indicatorOptions = [
    { value: "RSI", label: "RSI (Relative Strength Index)" },
    { value: "MACD", label: "MACD" },
    { value: "MACD_crossover", label: "MACD Crossover" },
    { value: "MA_50", label: "Moving Average (50)" },
    { value: "MA_200", label: "Moving Average (200)" },
  ];

  useEffect(() => {
    fetchAlerts();
  }, [symbol]);

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      setError(null);
      // If symbol is provided, filter by symbol; otherwise get all alerts
      const response = await alertAPI.getAlerts(symbol);
      setAlerts(response.alerts);
    } catch (err) {
      console.error("Error fetching alerts:", err);
      setError(err instanceof Error ? err.message : "Failed to fetch alerts");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAlert = async () => {
    try {
      setError(null);
      await alertAPI.createAlert(formData);
      setShowCreateForm(false);
      resetForm();
      fetchAlerts();
      onAlertCreated?.();
    } catch (err) {
      console.error("Error creating alert:", err);
      setError(err instanceof Error ? err.message : "Failed to create alert");
    }
  };

  const handleUpdateAlert = async (alertId: string, updates: Partial<Alert>) => {
    try {
      setError(null);
      await alertAPI.updateAlert(alertId, updates);
      fetchAlerts();
    } catch (err) {
      console.error("Error updating alert:", err);
      setError(err instanceof Error ? err.message : "Failed to update alert");
    }
  };

  const handleDeleteAlert = async (alertId: string) => {
    if (!confirm("Are you sure you want to delete this alert?")) {
      return;
    }
    try {
      setError(null);
      await alertAPI.deleteAlert(alertId);
      fetchAlerts();
    } catch (err) {
      console.error("Error deleting alert:", err);
      setError(err instanceof Error ? err.message : "Failed to delete alert");
    }
  };

  const resetForm = () => {
    setFormData({
      symbol: symbol || "BTC/USDT",
      alert_type: "price",
      enabled: true,
    });
    setEditingAlert(null);
  };

  const formatAlertDescription = (alert: Alert): string => {
    if (alert.alert_type === "price") {
      return `${alert.symbol} price ${alert.price_condition} $${alert.price_threshold?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    } else {
      return `${alert.symbol} ${alert.indicator_name} ${alert.indicator_condition} ${alert.indicator_value}`;
    }
  };

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-[#0a0a1a] to-[#1a1a2e]">
      {/* Header */}
      <div className="bg-dark-card/50 border-b border-gray-800 p-4 flex-shrink-0">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 bg-yellow-500 rounded-full" />
            <h2 className="text-xl font-bold text-white">🔔 Alert Manager</h2>
          </div>
          <button
            onClick={() => {
              resetForm();
              setShowCreateForm(true);
            }}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium text-white transition-colors flex items-center gap-2"
          >
            <Plus size={16} />
            New Alert
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-500/20 border border-red-500 rounded-lg p-3 m-4">
          <div className="text-red-400 text-sm">⚠️ {error}</div>
        </div>
      )}

      {/* Create/Edit Form */}
      {(showCreateForm || editingAlert) && (
        <div className="bg-dark-card rounded-lg p-4 m-4 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">
            {editingAlert ? "Edit Alert" : "Create New Alert"}
          </h3>
          <div className="space-y-4">
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Symbol</label>
              <select
                value={editingAlert?.symbol || formData.symbol}
                onChange={(e) =>
                  editingAlert
                    ? setEditingAlert({ ...editingAlert, symbol: e.target.value })
                    : setFormData({ ...formData, symbol: e.target.value })
                }
                className="w-full bg-dark-bg border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
              >
                {tradingPairs.map((pair) => (
                  <option key={pair} value={pair}>
                    {pair}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs text-gray-400 mb-1 block">Alert Type</label>
              <select
                value={editingAlert?.alert_type || formData.alert_type}
                onChange={(e) => {
                  const alertType = e.target.value as "price" | "indicator";
                  if (editingAlert) {
                    setEditingAlert({ ...editingAlert, alert_type: alertType });
                  } else {
                    setFormData({ ...formData, alert_type: alertType });
                  }
                }}
                className="w-full bg-dark-bg border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
              >
                <option value="price">Price Alert</option>
                <option value="indicator">Indicator Alert</option>
              </select>
            </div>

            {(editingAlert?.alert_type || formData.alert_type) === "price" ? (
              <>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">
                    Price Threshold
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={
                      editingAlert?.price_threshold?.toString() ||
                      formData.price_threshold?.toString() ||
                      ""
                    }
                    onChange={(e) => {
                      const value = parseFloat(e.target.value);
                      if (editingAlert) {
                        setEditingAlert({
                          ...editingAlert,
                          price_threshold: isNaN(value) ? undefined : value,
                        });
                      } else {
                        setFormData({
                          ...formData,
                          price_threshold: isNaN(value) ? undefined : value,
                        });
                      }
                    }}
                    className="w-full bg-dark-bg border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                    placeholder="Enter price threshold"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Condition</label>
                  <select
                    value={editingAlert?.price_condition || formData.price_condition || ""}
                    onChange={(e) => {
                      const condition = e.target.value as "above" | "below";
                      if (editingAlert) {
                        setEditingAlert({ ...editingAlert, price_condition: condition });
                      } else {
                        setFormData({ ...formData, price_condition: condition });
                      }
                    }}
                    className="w-full bg-dark-bg border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  >
                    <option value="">Select condition</option>
                    <option value="above">Above</option>
                    <option value="below">Below</option>
                  </select>
                </div>
              </>
            ) : (
              <>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Indicator</label>
                  <select
                    value={editingAlert?.indicator_name || formData.indicator_name || ""}
                    onChange={(e) => {
                      const indicatorName = e.target.value;
                      if (editingAlert) {
                        setEditingAlert({
                          ...editingAlert,
                          indicator_name: indicatorName as any,
                        });
                      } else {
                        setFormData({
                          ...formData,
                          indicator_name: indicatorName as any,
                        });
                      }
                    }}
                    className="w-full bg-dark-bg border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  >
                    <option value="">Select indicator</option>
                    {indicatorOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Condition</label>
                  <select
                    value={
                      editingAlert?.indicator_condition ||
                      formData.indicator_condition ||
                      ""
                    }
                    onChange={(e) => {
                      const condition = e.target.value as any;
                      if (editingAlert) {
                        setEditingAlert({
                          ...editingAlert,
                          indicator_condition: condition,
                        });
                      } else {
                        setFormData({ ...formData, indicator_condition: condition });
                      }
                    }}
                    className="w-full bg-dark-bg border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  >
                    <option value="">Select condition</option>
                    <option value="above">Above</option>
                    <option value="below">Below</option>
                    <option value="crosses_above">Crosses Above</option>
                    <option value="crosses_below">Crosses Below</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">
                    Indicator Value
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={
                      editingAlert?.indicator_value?.toString() ||
                      formData.indicator_value?.toString() ||
                      ""
                    }
                    onChange={(e) => {
                      const value = parseFloat(e.target.value);
                      if (editingAlert) {
                        setEditingAlert({
                          ...editingAlert,
                          indicator_value: isNaN(value) ? undefined : value,
                        });
                      } else {
                        setFormData({
                          ...formData,
                          indicator_value: isNaN(value) ? undefined : value,
                        });
                      }
                    }}
                    className="w-full bg-dark-bg border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                    placeholder="Enter threshold value"
                  />
                </div>
              </>
            )}

            <div>
              <label className="text-xs text-gray-400 mb-1 block">
                Description (Optional)
              </label>
              <input
                type="text"
                value={
                  editingAlert?.description ||
                  formData.description ||
                  ""
                }
                onChange={(e) => {
                  if (editingAlert) {
                    setEditingAlert({ ...editingAlert, description: e.target.value });
                  } else {
                    setFormData({ ...formData, description: e.target.value });
                  }
                }}
                className="w-full bg-dark-bg border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                placeholder="Optional description"
              />
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => {
                  if (editingAlert) {
                    handleUpdateAlert(editingAlert.id, {
                      enabled: editingAlert.enabled,
                      price_threshold: editingAlert.price_threshold,
                      price_condition: editingAlert.price_condition,
                      indicator_value: editingAlert.indicator_value,
                      description: editingAlert.description,
                    });
                    setEditingAlert(null);
                  } else {
                    handleCreateAlert();
                  }
                }}
                className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium text-white transition-colors"
              >
                {editingAlert ? "Update" : "Create"}
              </button>
              <button
                onClick={() => {
                  resetForm();
                  setShowCreateForm(false);
                }}
                className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm font-medium text-white transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Alerts List */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <div className="text-center py-12 text-gray-400">Loading alerts...</div>
        ) : alerts.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <Bell size={48} className="mx-auto mb-4 opacity-50" />
            <div>No alerts found</div>
            <button
              onClick={() => setShowCreateForm(true)}
              className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium text-white transition-colors"
            >
              Create Your First Alert
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className={`bg-dark-card rounded-lg p-4 border ${
                  alert.triggered
                    ? "border-green-500 bg-green-500/10"
                    : "border-gray-700"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="text-sm font-semibold text-white">
                        {alert.symbol}
                      </h3>
                      {alert.triggered ? (
                        <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded flex items-center gap-1">
                          <CheckCircle size={12} />
                          Triggered
                        </span>
                      ) : alert.enabled ? (
                        <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs rounded">
                          Active
                        </span>
                      ) : (
                        <span className="px-2 py-1 bg-gray-500/20 text-gray-400 text-xs rounded">
                          Disabled
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-300 mb-1">
                      {formatAlertDescription(alert)}
                    </p>
                    {alert.description && (
                      <p className="text-xs text-gray-500 mb-2">{alert.description}</p>
                    )}
                    <div className="text-xs text-gray-500">
                      Created: {new Date(alert.created_at).toLocaleString()}
                      {alert.triggered_at &&
                        ` • Triggered: ${new Date(alert.triggered_at).toLocaleString()}`}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    <button
                      onClick={() => {
                        handleUpdateAlert(alert.id, { enabled: !alert.enabled });
                      }}
                      className="p-2 hover:bg-gray-700 rounded transition-colors"
                      title={alert.enabled ? "Disable" : "Enable"}
                    >
                      {alert.enabled ? (
                        <ToggleRight size={20} className="text-blue-400" />
                      ) : (
                        <ToggleLeft size={20} className="text-gray-500" />
                      )}
                    </button>
                    <button
                      onClick={() => {
                        setEditingAlert(alert);
                        setShowCreateForm(false);
                      }}
                      className="p-2 hover:bg-gray-700 rounded transition-colors"
                      title="Edit"
                    >
                      <Edit size={18} className="text-gray-400" />
                    </button>
                    <button
                      onClick={() => handleDeleteAlert(alert.id)}
                      className="p-2 hover:bg-red-500/20 rounded transition-colors"
                      title="Delete"
                    >
                      <Trash2 size={18} className="text-red-400" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

