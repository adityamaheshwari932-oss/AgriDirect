import React, { useEffect, useState, useCallback } from "react";
import {
  CheckSquare,
  Eye,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  FileText,
  Clock,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { adminApi } from "../../api/admin";
import type { AdminVerificationFilterParams } from "../../types/admin";
import type { VerificationSubmission } from "../../types/verification";
import { LoadingState, ErrorState, EmptyState } from "../../components/ui/states";
import { AdminVerificationReviewModal } from "../../components/admin/AdminVerificationReviewModal";

export const AdminVerificationQueuePage: React.FC = () => {
  const [submissions, setSubmissions] = useState<VerificationSubmission[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 15;
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState("pending");
  const [roleFilter, setRoleFilter] = useState("");

  // Modal
  const [selectedSubmissionId, setSelectedSubmissionId] = useState<string | null>(null);

  const fetchVerifications = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params: AdminVerificationFilterParams = {
        page,
        page_size: pageSize,
      };
      if (statusFilter) params.status = statusFilter;
      if (roleFilter) params.role = roleFilter;

      const res = await adminApi.listVerifications(params);
      setSubmissions(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages || 1);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load verification applications.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [page, pageSize, statusFilter, roleFilter]);

  useEffect(() => {
    void fetchVerifications();
  }, [fetchVerifications]);

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case "approved":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-700 border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            Approved
          </span>
        );
      case "rejected":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-700 border border-rose-500/20">
            <XCircle className="w-3 h-3 text-rose-600" />
            Rejected
          </span>
        );
      case "pending":
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-700 border border-blue-500/20">
            <Clock className="w-3 h-3 text-blue-600" />
            Pending Review
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
          <CheckSquare className="w-6 h-6 text-primary" aria-hidden="true" />
          Administrative Identity Verification Queue
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Review legal identity credentials, land deeds, and corporate trade licenses submitted by platform users.
        </p>
      </div>

      {/* Filter Bar */}
      <div className="p-4 rounded-2xl bg-card border border-border shadow-xs flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          {/* Status Tabs */}
          {[
            { key: "pending", label: "Pending Review" },
            { key: "approved", label: "Approved" },
            { key: "rejected", label: "Rejected" },
            { key: "", label: "All Applications" },
          ].map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => {
                setStatusFilter(tab.key);
                setPage(1);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                statusFilter === tab.key
                  ? "bg-primary text-primary-foreground shadow-xs"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary"
              }`}
            >
              {tab.label}
            </button>
          ))}

          {/* Role Filter */}
          <select
            value={roleFilter}
            onChange={(e) => {
              setRoleFilter(e.target.value);
              setPage(1);
            }}
            className="px-2.5 py-1.5 rounded-lg border border-border bg-card text-foreground"
          >
            <option value="">All Applicant Roles</option>
            <option value="farmer">Farmer Applicants</option>
            <option value="buyer">Commercial Buyer Applicants</option>
          </select>
        </div>

        <button
          type="button"
          onClick={() => void fetchVerifications()}
          className="px-3 py-1.5 rounded-lg bg-secondary text-foreground hover:bg-secondary/80 font-semibold border border-border flex items-center gap-1.5 shrink-0"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Applications</span>
        </button>
      </div>

      {/* Table Area */}
      {error && <ErrorState message={error} onRetry={() => void fetchVerifications()} />}

      {isLoading ? (
        <LoadingState message="Loading verification applications queue..." />
      ) : submissions.length === 0 ? (
        <EmptyState
          title="No verification applications found"
          description="There are currently no verification submissions matching the selected review status."
        />
      ) : (
        <div className="bg-card border border-border rounded-2xl shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-secondary/40 text-muted-foreground font-semibold border-b border-border">
                <tr>
                  <th className="px-4 py-3">Applicant User</th>
                  <th className="px-4 py-3">Role</th>
                  <th className="px-4 py-3">Submission Notes</th>
                  <th className="px-4 py-3">Attached Documents</th>
                  <th className="px-4 py-3">Review Status</th>
                  <th className="px-4 py-3">Submitted Date</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {submissions.map((sub) => (
                  <tr key={sub.id} className="hover:bg-secondary/20 transition-colors">
                    <td className="px-4 py-3">
                      <div className="font-semibold text-foreground">
                        {sub.user_email || `User ${sub.user_id.slice(0, 8)}`}
                      </div>
                      <div className="text-[10px] text-muted-foreground font-mono">{sub.user_id}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="capitalize font-semibold text-foreground">
                        {sub.user_role || "applicant"}
                      </span>
                    </td>
                    <td className="px-4 py-3 max-w-xs truncate text-muted-foreground">
                      {sub.submission_notes || "—"}
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-secondary text-foreground">
                        <FileText className="w-3 h-3 text-primary" />
                        {sub.documents.length} document(s)
                      </span>
                    </td>
                    <td className="px-4 py-3">{renderStatusBadge(sub.status)}</td>
                    <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">
                      {new Date(sub.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        onClick={() => setSelectedSubmissionId(sub.id)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-primary hover:bg-primary/10 font-semibold transition-colors"
                        aria-label={`Review verification application ${sub.id}`}
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>{sub.status === "pending" ? "Review" : "Inspect"}</span>
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
                Page {page} of {totalPages} ({total} applications total)
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="p-1.5 rounded-lg border border-border hover:bg-secondary disabled:opacity-40"
                  aria-label="Previous page"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                  className="p-1.5 rounded-lg border border-border hover:bg-secondary disabled:opacity-40"
                  aria-label="Next page"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Verification Review Modal */}
      <AdminVerificationReviewModal
        submissionId={selectedSubmissionId}
        isOpen={Boolean(selectedSubmissionId)}
        onClose={() => setSelectedSubmissionId(null)}
        onSuccess={() => void fetchVerifications()}
      />
    </div>
  );
};

