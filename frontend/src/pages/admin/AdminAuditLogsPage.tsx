import React, { useEffect, useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import {
  History,
  Eye,
  ChevronLeft,
  ChevronRight,
  Lock,
} from "lucide-react";
import { adminApi } from "../../api/admin";
import type { AdminAuditLog, AdminAuditLogFilterParams } from "../../types/admin";
import { LoadingState, ErrorState, EmptyState } from "../../components/ui/states";
import { AdminAuditLogDetailModal } from "../../components/admin/AdminAuditLogDetailModal";
import { formatDateTime } from "../../utils/formatters";

export const AdminAuditLogsPage: React.FC = () => {
  const { t } = useTranslation(["admin", "common"]);
  const [logs, setLogs] = useState<AdminAuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [actionFilter, setActionFilter] = useState("");
  const [targetTypeFilter, setTargetTypeFilter] = useState("");
  const [adminUserIdFilter, setAdminUserIdFilter] = useState("");
  const [targetEntityIdFilter, setTargetEntityIdFilter] = useState("");

  // Modal
  const [selectedLog, setSelectedLog] = useState<AdminAuditLog | null>(null);

  const fetchLogs = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params: AdminAuditLogFilterParams = {
        page,
        page_size: pageSize,
      };
      if (actionFilter.trim()) params.action = actionFilter.trim();
      if (targetTypeFilter.trim()) params.target_entity_type = targetTypeFilter.trim();
      if (adminUserIdFilter.trim()) params.admin_user_id = adminUserIdFilter.trim();
      if (targetEntityIdFilter.trim()) params.target_entity_id = targetEntityIdFilter.trim();

      const res = await adminApi.listAuditLogs(params);
      setLogs(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages || 1);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t("admin:load_error", "Failed to load audit logs.");
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [page, pageSize, actionFilter, targetTypeFilter, adminUserIdFilter, targetEntityIdFilter, t]);

  useEffect(() => {
    void fetchLogs();
  }, [fetchLogs]);

  const handleFilterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    void fetchLogs();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <History className="w-6 h-6 text-primary" aria-hidden="true" />
            <span>{t("admin:audit_trail_title", "Platform Governance Audit Trail")}</span>
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {t("admin:audit_trail_subtitle", "Immutable, cryptographically verifiable ledger of all privileged administrative decisions and moderations.")}
          </p>
        </div>

        <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-secondary text-muted-foreground text-xs font-semibold border border-border self-start sm:self-center">
          <Lock className="w-3.5 h-3.5 text-primary" />
          <span>{t("admin:strictly_read_only", "Strictly Read-Only Trail")}</span>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="p-4 rounded-2xl bg-card border border-border shadow-xs space-y-3">
        <form onSubmit={handleFilterSubmit} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          <div>
            <label className="text-[10px] uppercase font-bold text-muted-foreground block mb-1">
              {t("admin:th_action", "Action Name")}
            </label>
            <input
              type="text"
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              placeholder={t("admin:action_placeholder", "e.g. user_status_update...")}
              className="w-full px-3 py-1.5 rounded-lg border border-border bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div>
            <label className="text-[10px] uppercase font-bold text-muted-foreground block mb-1">
              {t("admin:th_target_entity", "Target Entity Type")}
            </label>
            <input
              type="text"
              value={targetTypeFilter}
              onChange={(e) => setTargetTypeFilter(e.target.value)}
              placeholder="e.g. user, listing, requirement..."
              className="w-full px-3 py-1.5 rounded-lg border border-border bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div>
            <label className="text-[10px] uppercase font-bold text-muted-foreground block mb-1">
              {t("admin:th_admin_id", "Administrator ID")}
            </label>
            <input
              type="text"
              value={adminUserIdFilter}
              onChange={(e) => setAdminUserIdFilter(e.target.value)}
              placeholder="Admin UUID..."
              className="w-full px-3 py-1.5 rounded-lg border border-border bg-card text-foreground placeholder:text-muted-foreground font-mono focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div className="flex items-end gap-2">
            <div className="flex-1">
              <label className="text-[10px] uppercase font-bold text-muted-foreground block mb-1">
                {t("admin:target_entity_id", "Target Entity ID")}
              </label>
              <input
                type="text"
                value={targetEntityIdFilter}
                onChange={(e) => setTargetEntityIdFilter(e.target.value)}
                placeholder="Entity UUID..."
                className="w-full px-3 py-1.5 rounded-lg border border-border bg-card text-foreground placeholder:text-muted-foreground font-mono focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
            <button
              type="submit"
              className="px-3.5 py-1.5 rounded-lg bg-primary text-primary-foreground font-semibold hover:bg-primary/90 transition-colors shadow-xs shrink-0 h-[32px]"
            >
              {t("common:actions.filter", "Filter")}
            </button>
          </div>
        </form>
      </div>

      {/* Table Area */}
      {error && <ErrorState message={error} onRetry={() => void fetchLogs()} />}

      {isLoading ? (
        <LoadingState message={t("admin:loading_audit", "Loading governance audit logs...")} />
      ) : logs.length === 0 ? (
        <EmptyState
          title={t("admin:empty_audit_title", "No audit logs found")}
          description={t("admin:empty_audit_desc", "No administrative activity records match the current filter criteria.")}
        />
      ) : (
        <div className="bg-card border border-border rounded-2xl shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-start text-xs">
              <thead className="bg-secondary/40 text-muted-foreground font-semibold border-b border-border">
                <tr>
                  <th className="px-4 py-3">{t("common:labels.date", "Timestamp (UTC)")}</th>
                  <th className="px-4 py-3">{t("admin:th_action", "Privileged Action")}</th>
                  <th className="px-4 py-3">{t("admin:th_target_entity", "Target Entity")}</th>
                  <th className="px-4 py-3">{t("admin:th_admin_id", "Administrator ID")}</th>
                  <th className="px-4 py-3">{t("admin:th_rationale", "Recorded Rationale")}</th>
                  <th className="px-4 py-3">{t("admin:th_ip_address", "IP Address")}</th>
                  <th className="px-4 py-3 text-end">{t("admin:th_inspect", "Inspect")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-secondary/20 transition-colors">
                    <td className="px-4 py-3 whitespace-nowrap text-muted-foreground">
                      {formatDateTime(log.created_at)}
                    </td>
                    <td className="px-4 py-3 font-semibold text-foreground">
                      <span className="font-mono text-xs">{log.action}</span>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-secondary text-foreground capitalize me-1.5">
                        {log.target_entity_type}
                      </span>
                      <span className="font-mono text-[10px] text-muted-foreground/80">{log.target_entity_id.slice(0, 8)}...</span>
                    </td>
                    <td className="px-4 py-3 font-mono text-[11px] text-muted-foreground">
                      {log.admin_user_id.slice(0, 8)}...
                    </td>
                    <td className="px-4 py-3 max-w-xs truncate text-muted-foreground italic">
                      {log.reason || "—"}
                    </td>
                    <td className="px-4 py-3 font-mono text-[11px] text-muted-foreground">
                      {log.ip_address || "—"}
                    </td>
                    <td className="px-4 py-3 text-end">
                      <button
                        type="button"
                        onClick={() => setSelectedLog(log)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-primary hover:bg-primary/10 font-semibold transition-colors"
                        aria-label={`Inspect audit log ${log.id}`}
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>{t("admin:btn_inspect", "Inspect")}</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="px-4 py-3 border-t border-border flex items-center justify-between text-xs text-muted-foreground">
              <span>
                {t("common:pagination.showing_page", `Page ${page} of ${totalPages} (${total} audit log records)`, {
                  page,
                  totalPages,
                  count: total,
                })}
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="p-1.5 rounded-lg border border-border hover:bg-secondary disabled:opacity-40"
                  aria-label={t("common:pagination.previous", "Previous page")}
                >
                  <ChevronLeft className="w-4 h-4 rtl:rotate-180" />
                </button>
                <button
                  type="button"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                  className="p-1.5 rounded-lg border border-border hover:bg-secondary disabled:opacity-40"
                  aria-label={t("common:pagination.next", "Next page")}
                >
                  <ChevronRight className="w-4 h-4 rtl:rotate-180" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Audit Log Detail Modal */}
      <AdminAuditLogDetailModal
        log={selectedLog}
        isOpen={Boolean(selectedLog)}
        onClose={() => setSelectedLog(null)}
      />
    </div>
  );
};

