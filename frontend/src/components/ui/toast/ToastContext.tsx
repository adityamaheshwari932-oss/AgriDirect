import React, {
  createContext,
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { Toast, ToastVariant } from "./ToastItem";
import { ToastContainer } from "./ToastContainer";

export interface ToastOptions {
  id?: string;
  title?: string;
  message: string;
  variant?: ToastVariant;
  duration?: number;
}

export interface ToastContextValue {
  toasts: Toast[];
  showToast: (options: ToastOptions) => string;
  success: (message: string, title?: string, duration?: number) => string;
  error: (message: string, title?: string, duration?: number) => string;
  warning: (message: string, title?: string, duration?: number) => string;
  info: (message: string, title?: string, duration?: number) => string;
  dismissToast: (id: string) => void;
  clearToasts: () => void;
}

export const ToastContext = createContext<ToastContextValue | null>(null);

const DEFAULT_DURATION = 5000;
const MAX_TOASTS = 5;
const DEDUPLICATION_WINDOW_MS = 1500;

interface ToastProviderProps {
  children: ReactNode;
  maxToasts?: number;
  defaultDuration?: number;
}

export const ToastProvider: React.FC<ToastProviderProps> = ({
  children,
  maxToasts = MAX_TOASTS,
  defaultDuration = DEFAULT_DURATION,
}) => {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());
  const recentToastsRef = useRef<Map<string, number>>(new Map());

  const dismissToast = useCallback((id: string) => {
    // Clear associated timer if active
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }

    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const clearToasts = useCallback(() => {
    // Clear all timers
    timersRef.current.forEach((timer) => clearTimeout(timer));
    timersRef.current.clear();
    recentToastsRef.current.clear();
    setToasts([]);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    const currentTimers = timersRef.current;
    return () => {
      currentTimers.forEach((timer) => clearTimeout(timer));
      currentTimers.clear();
    };
  }, []);

  const showToast = useCallback(
    (options: ToastOptions): string => {
      const variant: ToastVariant = options.variant || "info";
      const message = options.message;
      const title = options.title;
      const duration = options.duration !== undefined ? options.duration : defaultDuration;

      // Deduplication check: prevent identical toast flooding within window
      const dedupKey = `${variant}:${title || ""}:${message}`;
      const now = Date.now();
      const lastSeen = recentToastsRef.current.get(dedupKey);

      if (lastSeen && now - lastSeen < DEDUPLICATION_WINDOW_MS) {
        // Return existing or synthetic id without duplicating
        return options.id || dedupKey;
      }
      recentToastsRef.current.set(dedupKey, now);

      // Clean up dedup map periodically
      if (recentToastsRef.current.size > 50) {
        recentToastsRef.current.forEach((time, key) => {
          if (now - time > DEDUPLICATION_WINDOW_MS * 2) {
            recentToastsRef.current.delete(key);
          }
        });
      }

      const id =
        options.id ||
        `toast-${now}-${Math.random().toString(36).substring(2, 8)}`;

      const newToast: Toast = {
        id,
        title,
        message,
        variant,
        duration,
      };

      setToasts((prev) => {
        // Enforce maximum active toasts
        const next = [...prev.filter((t) => t.id !== id), newToast];
        if (next.length > maxToasts) {
          const removed = next.slice(0, next.length - maxToasts);
          removed.forEach((item) => {
            const timer = timersRef.current.get(item.id);
            if (timer) {
              clearTimeout(timer);
              timersRef.current.delete(item.id);
            }
          });
          return next.slice(next.length - maxToasts);
        }
        return next;
      });

      // Set auto-dismiss timer if duration > 0
      if (duration > 0) {
        // Clear any existing timer for this ID first
        const existingTimer = timersRef.current.get(id);
        if (existingTimer) {
          clearTimeout(existingTimer);
        }

        const timer = setTimeout(() => {
          dismissToast(id);
        }, duration);

        timersRef.current.set(id, timer);
      }

      return id;
    },
    [defaultDuration, dismissToast, maxToasts]
  );

  const success = useCallback(
    (message: string, title?: string, duration?: number) =>
      showToast({ message, title, variant: "success", duration }),
    [showToast]
  );

  const error = useCallback(
    (message: string, title?: string, duration?: number) =>
      showToast({ message, title, variant: "error", duration }),
    [showToast]
  );

  const warning = useCallback(
    (message: string, title?: string, duration?: number) =>
      showToast({ message, title, variant: "warning", duration }),
    [showToast]
  );

  const info = useCallback(
    (message: string, title?: string, duration?: number) =>
      showToast({ message, title, variant: "info", duration }),
    [showToast]
  );

  const value: ToastContextValue = {
    toasts,
    showToast,
    success,
    error,
    warning,
    info,
    dismissToast,
    clearToasts,
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </ToastContext.Provider>
  );
};

