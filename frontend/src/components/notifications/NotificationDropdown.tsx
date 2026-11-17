import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Bell,
  CheckCheck,
  Loader2,
  Package,
  Handshake,
  Tag,
  ShieldCheck,
  AlertCircle,
} from "lucide-react";
import { notificationsApi } from "../../api/notifications";
import type { NotificationItem } from "../../types/notifications";
import { formatDateTime } from "../../utils/formatters";

interface NotificationDropdownProps {
  isOpen: boolean;
  onClose: () => void;
  onUnreadCountChanged?: () => void;
}

export const NotificationDropdown: React.FC<NotificationDropdownProps> = ({
  isOpen,
  onClose,
  onUnreadCountChanged,
}) => {
  const { t } = useTranslation(["notifications", "common"]);
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isMarkingAll, setIsMarkingAll] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;
    setIsLoading(true);
    setError(null);

    notificationsApi
      .listNotifications(1, 15)
      .then((res) => {
        if (!isMounted) return;
        setNotifications(res.items);
      })
      .catch((err: unknown) => {
        if (!isMounted) return;
        const msg = err instanceof Error ? err.message : "Failed to load notifications.";
        setError(msg);
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const handleMarkAllRead = async () => {
    setIsMarkingAll(true);
    try {
      await notificationsApi.markAllRead();
      setNotifications((prev) =>
        prev.map((n) => ({ ...n, is_read: true, read_at: new Date().toISOString() }))
      );
      if (onUnreadCountChanged) onUnreadCountChanged();
    } catch {
      // Best-effort
    } finally {
      setIsMarkingAll(false);
    }
  };

  const handleNotificationClick = async (notif: NotificationItem) => {
    if (!notif.is_read) {
      try {
        await notificationsApi.markNotificationRead(notif.id);
        setNotifications((prev) =>
          prev.map((n) =>
            n.id === notif.id ? { ...n, is_read: true, read_at: new Date().toISOString() } : n
          )
        );
        if (onUnreadCountChanged) onUnreadCountChanged();
      } catch {
        // Continue navigation
      }
    }

    onClose();

    // Deep link based on supported reference types
    if (notif.reference_type === "order") {
      navigate("/dashboard/orders");
    } else if (notif.reference_type === "offer") {
      navigate("/dashboard/offers");
    } else if (notif.reference_type === "listing") {
      navigate("/dashboard/listings");
    } else if (notif.reference_type === "verification") {
      navigate("/dashboard/profile");
    }
  };

  const getReferenceIcon = (refType?: string | null) => {
    switch (refType) {
      case "order":
        return <Package className="w-4 h-4 text-primary" />;
      case "offer":
        return <Handshake className="w-4 h-4 text-blue-500" />;
      case "listing":
        return <Tag className="w-4 h-4 text-emerald-500" />;
      case "verification":
        return <ShieldCheck className="w-4 h-4 text-amber-500" />;
      default:
        return <Bell className="w-4 h-4 text-muted-foreground" />;
    }
  };

  return (
    <div className="absolute end-0 mt-2 w-80 sm:w-96 bg-card border border-border rounded-xl shadow-xl z-50 overflow-hidden flex flex-col animate-in fade-in slide-in-from-top-2 duration-150">
      {/* Header */}
      <div className="p-3.5 border-b border-border bg-secondary/30 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bell className="w-4 h-4 text-primary" />
          <span className="text-xs font-bold text-foreground">
            {t("notifications:title", "Notifications")}
          </span>
        </div>
        <button
          type="button"
          onClick={handleMarkAllRead}
          disabled={isMarkingAll || notifications.every((n) => n.is_read)}
          className="inline-flex items-center gap-1 text-[11px] font-medium text-primary hover:underline disabled:opacity-40 disabled:no-underline transition-colors"
        >
          {isMarkingAll ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : (
            <CheckCheck className="w-3 h-3" />
          )}
          {t("notifications:mark_all_read", "Mark all read")}
        </button>
      </div>

      {/* Body */}
      <div className="max-h-96 overflow-y-auto divide-y divide-border">
        {isLoading ? (
          <div className="py-10 flex flex-col items-center justify-center gap-2 text-muted-foreground">
            <Loader2 className="w-5 h-5 animate-spin text-primary" />
            <span className="text-xs">{t("common:status.loading", "Loading alerts...")}</span>
          </div>
        ) : error ? (
          <div className="p-4 text-center text-xs text-destructive flex items-center justify-center gap-1.5">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        ) : notifications.length === 0 ? (
          <div className="py-12 px-4 text-center text-muted-foreground space-y-1">
            <Bell className="w-8 h-8 opacity-20 mx-auto" />
            <p className="text-xs font-medium text-foreground">
              {t("notifications:empty_title", "No notifications")}
            </p>
            <p className="text-[11px]">
              {t("notifications:empty_desc", "You're all caught up with your orders and offers.")}
            </p>
          </div>
        ) : (
          notifications.map((notif) => {
            const timeAgo = formatDateTime(notif.created_at);

            return (
              <button
                key={notif.id}
                type="button"
                onClick={() => void handleNotificationClick(notif)}
                className={`w-full text-start p-3.5 flex items-start gap-3 transition-colors hover:bg-secondary/40 focus:outline-none ${
                  !notif.is_read ? "bg-primary-50/40" : ""
                }`}
              >
                <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center shrink-0 border border-border">
                  {getReferenceIcon(notif.reference_type)}
                </div>

                <div className="flex-1 min-w-0 space-y-0.5">
                  <div className="flex items-center justify-between gap-1">
                    <span className="text-xs font-semibold text-foreground truncate">
                      {notif.title}
                    </span>
                    {!notif.is_read && (
                      <span className="w-2 h-2 rounded-full bg-primary shrink-0" />
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                    {notif.body}
                  </p>
                  <span className="text-[10px] text-muted-foreground/80 block pt-0.5">
                    {timeAgo}
                  </span>
                </div>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
};

