import React, { useEffect, useRef, useState } from "react";
import { Bell } from "lucide-react";
import { notificationsApi } from "../../api/notifications";
import { NotificationDropdown } from "./NotificationDropdown";

export const NotificationBell: React.FC = () => {
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const fetchUnreadCount = async () => {
    try {
      const res = await notificationsApi.getUnreadCount();
      setUnreadCount(res.unread_count);
    } catch {
      // Best-effort
    }
  };

  useEffect(() => {
    void fetchUnreadCount();

    const interval = setInterval(() => {
      if (!document.hidden) {
        void fetchUnreadCount();
      }
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  // Click outside listener
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        aria-label={`Notifications (${unreadCount} unread)`}
        onClick={() => setIsOpen((prev) => !prev)}
        className="relative p-2 rounded-lg text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors focus:outline-none focus:ring-1 focus:ring-primary"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white bg-destructive rounded-full shadow-xs">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      <NotificationDropdown
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        onUnreadCountChanged={fetchUnreadCount}
      />
    </div>
  );
};

