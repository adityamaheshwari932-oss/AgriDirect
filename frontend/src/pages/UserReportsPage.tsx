import React, { useEffect, useState, useCallback } from "react";
import {
  ShieldAlert,
  Plus,
  AlertCircle,
  Loader2,
  Clock,
  CheckCircle2,
  Filter,
  Eye,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { reportsApi } from "../api/reports";
import { ReportCreateModal } from "../components/reports/ReportCreateModal";
import { ReportDetailModal } from "../components/reports/ReportDetailModal";
import type { ReportItem, ReportStatus } from "../types/reports";

const CATEGORY_LABELS: Record<string, string> = {
  payment: "Payment Issue",
  quantity_mismatch: "Quantity Mismatch",
  quality_issue: "Quality Issue",
  fraud: "Fraudulent Activity",
  harassment: "Harassment",
  other: "Other Concern",
};

export const UserReportsPage: React.FC = () => {
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 10;
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Status Filter
  const [statusFilter, setStatusFilter] = useState<string>("all");

  // Modals
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);

  const fetchReports = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await reportsApi.listMyReports(page, pageSize);
      setReports(response.items);
      setTotal(response.total);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load reports.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [page, pageSize]);

  useEffect(() => {
    void fetchReports();
  }, [fetchReports]);

  const filteredReports = statusFilter === "all"
    ? reports
    : reports.filter((r) => r.status === statusFilter);

  const totalPages = Math.ceil(total / pageSize) || 1;

  const renderStatusBadge = (status: ReportStatus | string) => {
    switch (status) {
      case "open":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-700 border border-amber-500/20">
            <Clock className="w-3 h-3 text-amber-600" aria-hidden="true" />
            Open Intake
          </span>
        );
      case "under_review":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-700 border border-blue-500/20">
            <Clock className="w-3 h-3 text-blue-600" aria-hidden="true" />
            Under Investigation
          </span>
        );
      case "action_taken":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-700 border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" aria-hidden="true" />
            Action Taken
          </span>
        );
      case "dismissed":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-secondary text-muted-foreground border border-border">
            Dismissed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-secondary text-foreground capitalize">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <ShieldAlert className="w-6 h-6 text-primary" aria-hidden="true" />
            Safety & Incident Reports
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Track grievances filed regarding counterparty conduct, settlement defaults, or marketplace violations.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setIsCreateOpen(true)}
          className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-semibold text-xs shadow-xs hover:bg-primary/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>File Incident Report</span>
        </button>
      </div>

      {/* Filter and Tab Bar */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 border-b border-border">
        <Filter className="w-4 h-4 text-muted-foreground shrink-0 ml-1" />
        {[
          { key: "all", label: "All Reports" },
          { key: "open", label: "Open Intake" },
          { key: "under_review", label: "Under Review" },
          { key: "action_taken", label: "Action Taken" },
          { key: "dismissed", label: "Dismissed" },
        ].map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setStatusFilter(tab.key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
              statusFilter === tab.key
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      {error && (
        <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}

      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-16 space-y-3">
          <Loader2 className="w-8 h-8 text-primary animate-spin" />
          <p className="text-sm text-muted-foreground">Loading your reports...</p>
        </div>
      ) : filteredReports.length === 0 ? (
        <div className="p-12 text-center rounded-2xl border border-dashed border-border bg-card/50 space-y-3">
          <ShieldAlert className="w-10 h-10 text-muted-foreground/60 mx-auto" />
          <h3 className="font-semibold text-foreground text-sm">No Reports Found</h3>
          <p className="text-xs text-muted-foreground max-w-sm mx-auto">
            {statusFilter === "all"
              ? "You haven't filed any safety reports. The marketplace maintains strict compliance standards."
              : `No reports match the status "${statusFilter}".`}
          </p>
        </div>
      ) : (
        <div className="bg-card border border-border rounded-2xl shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-secondary/40 text-muted-foreground font-semibold border-b border-border">
                <tr>
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3">Narrative Excerpt</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Resolution Notes</th>
                  <th className="px-4 py-3">Date Filed</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredReports.map((report) => (
                  <tr key={report.id} className="hover:bg-secondary/20 transition-colors">
                    <td className="px-4 py-3 font-semibold text-foreground">
                      {CATEGORY_LABELS[report.category] || report.category}
                    </td>
                    <td className="px-4 py-3 max-w-xs truncate text-muted-foreground">
                      {report.description}
                    </td>
                    <td className="px-4 py-3">{renderStatusBadge(report.status)}</td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {report.admin_notes ? (
                        <span className="inline-flex items-center gap-1 text-emerald-700 dark:text-emerald-400 font-medium text-[11px]">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Notes Available
                        </span>
                      ) : (
                        <span className="text-muted-foreground/75 italic text-[11px]">
                          Pending review
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">
                      {new Date(report.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        onClick={() => setSelectedReportId(report.id)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-primary hover:bg-primary/10 font-semibold transition-colors"
                        aria-label={`View report ${report.id}`}
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>View</span>
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
                Page {page} of {totalPages} ({total} reports)
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="p-1.5 rounded-lg border border-border hover:bg-secondary disabled:opacity-40 transition-colors"
                  aria-label="Previous page"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                  className="p-1.5 rounded-lg border border-border hover:bg-secondary disabled:opacity-40 transition-colors"
                  aria-label="Next page"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Modals */}
      <ReportCreateModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onSuccess={() => {
          void fetchReports();
        }}
      />

      <ReportDetailModal
        reportId={selectedReportId}
        isOpen={Boolean(selectedReportId)}
        onClose={() => setSelectedReportId(null)}
      />
    </div>
  );
};

