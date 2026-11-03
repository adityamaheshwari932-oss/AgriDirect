import React from "react";
import { X, History, Shield, Calendar, Globe, User, Hash } from "lucide-react";
import type { AdminAuditLog } from "../../types/admin";

interface AdminAuditLogDetailModalProps {
  log: AdminAuditLog | null;
  isOpen: boolean;
  onClose: () => void;
}

export const AdminAuditLogDetailModal: React.FC<AdminAuditLogDetailModalProps> = ({
  log,
  isOpen,
  onClose,
}) => {
  if (!isOpen || !log) return null;

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-audit-log-title"
    >
      <div className="bg-card w-full max-w-lg rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/40">
          <div className="flex items-center gap-2.5">
            <History className="w-5 h-5 text-primary" aria-hidden="true" />
            <div>
              <h2 id="modal-audit-log-title" className="text-base font-bold text-foreground">
                Audit Trail Record
              </h2>
              <p className="text-[11px] text-muted-foreground">
                Immutable Platform Governance Action Log
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary focus:outline-none focus:ring-2 focus:ring-primary"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        {/* Content - Strictly Read-Only */}
        <div className="p-6 space-y-4 text-xs">
          {/* Action Header Card */}
          <div className="p-3.5 rounded-xl bg-secondary/30 border border-border flex items-center justify-between">
            <div>
              <span className="text-[10px] uppercase font-bold text-muted-foreground block">
                Privileged Action
              </span>
              <span className="font-bold text-foreground text-sm">{log.action}</span>
            </div>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-primary/10 text-primary border border-primary/20 capitalize">
              {log.target_entity_type}
            </span>
          </div>

          {/* Details Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="p-3 rounded-lg border border-border bg-card space-y-0.5">
              <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                <Hash className="w-3 h-3" /> Audit Record ID
              </span>
              <span className="font-mono text-[11px] text-foreground break-all">{log.id}</span>
            </div>

            <div className="p-3 rounded-lg border border-border bg-card space-y-0.5">
              <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                <User className="w-3 h-3" /> Administrator ID
              </span>
              <span className="font-mono text-[11px] text-foreground break-all">{log.admin_user_id}</span>
            </div>

            <div className="p-3 rounded-lg border border-border bg-card space-y-0.5">
              <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                <Shield className="w-3 h-3" /> Target Entity ID
              </span>
              <span className="font-mono text-[11px] text-foreground break-all">{log.target_entity_id}</span>
            </div>

            <div className="p-3 rounded-lg border border-border bg-card space-y-0.5">
              <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                <Globe className="w-3 h-3" /> Origin IP Address
              </span>
              <span className="font-mono text-[11px] text-foreground">{log.ip_address || "Unavailable"}</span>
            </div>

            <div className="sm:col-span-2 p-3 rounded-lg border border-border bg-card space-y-0.5">
              <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                <Calendar className="w-3 h-3" /> Recorded Timestamp (UTC)
              </span>
              <span className="font-medium text-foreground">
                {new Date(log.created_at).toUTCString()} ({new Date(log.created_at).toLocaleString()})
              </span>
            </div>
          </div>

          {/* Justification / Reason */}
          <div className="space-y-1.5">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground block">
              Recorded Rationale / Notes
            </span>
            <div className="p-3.5 rounded-xl bg-card border border-border text-xs leading-relaxed text-foreground whitespace-pre-wrap">
              {log.reason || "No rationale string was recorded for this system action."}
            </div>
          </div>

          <div className="p-3 rounded-xl bg-secondary/30 border border-border text-[11px] text-muted-foreground flex items-center gap-2">
            <Shield className="w-4 h-4 text-primary shrink-0" />
            <span>Audit log entries are cryptographically protected and immutable. Modifications and deletions are strictly disabled.</span>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-border flex justify-end bg-secondary/20">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-secondary text-foreground hover:bg-secondary/80 text-xs font-semibold border border-border transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

