import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, AlertCircle } from "lucide-react";
import { Notification } from "../types/notification";
import { aiAPI, ChatMessage } from "../services/api";
import { tradingAPI } from "../services/api";

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  notificationId?: string;
}

interface CommandCenterProps {
  selectedNotification?: Notification | null;
  onActionRequest?: (action: string, params: any) => void; // Will be used in Phase 4
}

// Track analyzed notification IDs in localStorage to persist across component mounts
const getAnalyzedIds = (): Set<string> => {
  const stored = localStorage.getItem("analyzedNotificationIds");
  return new Set(stored ? JSON.parse(stored) : []);
};

const markAsAnalyzed = (id: string) => {
  const ids = getAnalyzedIds();
  ids.add(id);
  localStorage.setItem(
    "analyzedNotificationIds",
    JSON.stringify(Array.from(ids))
  );
};

export function CommandCenter({ selectedNotification }: CommandCenterProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "system",
      content:
        "Command Center Online. All systems operational. Ready for tactical analysis.",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [aiEnabled, setAiEnabled] = useState<boolean | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Check AI status on mount
  useEffect(() => {
    aiAPI
      .getStatus()
      .then((status) => setAiEnabled(status.enabled))
      .catch(() => setAiEnabled(false));
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const notificationId = selectedNotification?.id;

    // Skip if no notification, or if we've already analyzed this exact notification
    if (!notificationId || getAnalyzedIds().has(notificationId)) {
      return;
    }

    // Mark as analyzed immediately to prevent duplicate analysis
    markAsAnalyzed(notificationId);

    if (aiEnabled) {
      // Auto-analyze notification when selected
      setIsLoading(true);

      // Get context (positions, balance) for AI
      Promise.all([
        tradingAPI.getPositions().catch(() => ({ positions: [] })),
        tradingAPI.getBalance().catch(() => ({ balance: 0 })),
      ]).then(([positionsData, balanceData]) => {
        if (!selectedNotification) {
          setIsLoading(false);
          return;
        }

        const context = {
          positions: positionsData.positions || [],
          balance: balanceData.balance || 0,
          selected_notification: {
            id: selectedNotification.id,
            title: selectedNotification.title,
            type: selectedNotification.type,
            symbol: selectedNotification.symbol,
            confidence_score: selectedNotification.confidence_score,
            urgency_score: selectedNotification.urgency_score,
            message: selectedNotification.message,
          },
        };

        aiAPI
          .analyzeNotification(selectedNotification, context)
          .then((analysis) => {
            const analysisMessage: Message = {
              id: `analysis-${Date.now()}`,
              role: "assistant",
              content: analysis,
              timestamp: new Date(),
              notificationId: selectedNotification.id,
            };
            setMessages((prev) => [...prev, analysisMessage]);
            setIsLoading(false);
          })
          .catch((error) => {
            const errorMessage: Message = {
              id: `error-${Date.now()}`,
              role: "assistant",
              content: `⚠️ Error analyzing notification: ${error.message}`,
              timestamp: new Date(),
              notificationId: selectedNotification.id,
            };
            setMessages((prev) => [...prev, errorMessage]);
            setIsLoading(false);
          });
      });
    } else if (aiEnabled === false) {
      // AI not enabled, show basic info (only once)
      if (!selectedNotification) return;

      const analysisMessage: Message = {
        id: `analysis-${Date.now()}`,
        role: "assistant",
        content: `Analyzing notification: "${
          selectedNotification.title
        }"\n\nSignal detected: ${selectedNotification.type}\nConfidence: ${
          selectedNotification.confidence_score || "N/A"
        }%\nSymbol: ${
          selectedNotification.symbol || "N/A"
        }\n\n⚠️ AI analysis not available. Please configure OpenAI API key.`,
        timestamp: new Date(),
        notificationId: selectedNotification.id,
      };
      setMessages((prev) => [...prev, analysisMessage]);
    }
  }, [selectedNotification?.id, aiEnabled, selectedNotification]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const userInput = input;
    setInput("");
    setIsLoading(true);

    try {
      // Get context for AI
      const [positionsData, balanceData] = await Promise.all([
        tradingAPI.getPositions().catch(() => ({ positions: [] })),
        tradingAPI.getBalance().catch(() => ({ balance: 0 })),
      ]);

      const context = {
        positions: positionsData.positions || [],
        balance: balanceData.balance || 0,
        selected_notification: selectedNotification
          ? {
              id: selectedNotification.id,
              title: selectedNotification.title,
              type: selectedNotification.type,
              symbol: selectedNotification.symbol,
              confidence_score: selectedNotification.confidence_score,
            }
          : undefined,
      };

      // Build conversation history
      const conversationHistory: ChatMessage[] = messages
        .filter((m) => m.role !== "system")
        .map((m) => ({
          role: m.role as "user" | "assistant",
          content: m.content,
        }));

      // Call AI API
      const response = await aiAPI.chat(
        userInput,
        conversationHistory,
        context
      );

      const aiMessage: Message = {
        id: `ai-${Date.now()}`,
        role: "assistant",
        content: response,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: `⚠️ Error: ${
          error instanceof Error ? error.message : "Failed to get AI response"
        }\n\nPlease check that OpenAI API key is configured.`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-[#0a0a1a] to-[#1a1a2e]">
      {/* Header */}
      <div className="bg-dark-card/50 border-b border-gray-800 p-4">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse" />
          <h2 className="text-xl font-bold text-white">⚔️ Command Center</h2>
          <span className="text-xs text-gray-400 ml-auto">
            Tactical AI Assistant
          </span>
        </div>
        <div className="flex items-center justify-between mt-2">
          {selectedNotification && (
            <div className="text-sm text-gray-400">
              Analyzing:{" "}
              <span className="text-yellow-400">
                {selectedNotification.title}
              </span>
            </div>
          )}
          {aiEnabled === false && (
            <div className="flex items-center gap-2 text-xs text-yellow-400 bg-yellow-400/10 border border-yellow-400/20 rounded px-2 py-1">
              <AlertCircle size={14} />
              AI not configured
            </div>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex gap-3 ${
              message.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            {message.role !== "user" && (
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center flex-shrink-0">
                {message.role === "assistant" ? (
                  <Bot size={18} className="text-white" />
                ) : (
                  <span className="text-white text-xs">⚔️</span>
                )}
              </div>
            )}
            <div
              className={`max-w-[80%] rounded-lg p-3 ${
                message.role === "user"
                  ? "bg-blue-600 text-white"
                  : message.role === "system"
                  ? "bg-gray-800 text-gray-300 border border-gray-700"
                  : "bg-dark-card text-gray-100 border border-gray-700"
              }`}
            >
              <div className="whitespace-pre-wrap text-sm">
                {message.content}
              </div>
              <div className="text-xs opacity-70 mt-1">
                {message.timestamp.toLocaleTimeString()}
              </div>
            </div>
            {message.role === "user" && (
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-green-600 to-blue-600 flex items-center justify-center flex-shrink-0">
                <User size={18} className="text-white" />
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="flex gap-3 justify-start">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
              <Bot size={18} className="text-white" />
            </div>
            <div className="bg-dark-card rounded-lg p-3 border border-gray-700">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                <span
                  className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: "0.1s" }}
                />
                <span
                  className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: "0.2s" }}
                />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-800 p-4">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Enter tactical command or question..."
            className="flex-1 bg-dark-bg border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 resize-none"
            rows={2}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg text-white font-medium transition-colors flex items-center gap-2"
          >
            <Send size={18} />
            Send
          </button>
        </div>
        <div className="mt-2 text-xs text-gray-500">
          Press Enter to send, Shift+Enter for new line
        </div>
      </div>
    </div>
  );
}
