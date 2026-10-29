import React from "react";
import { History, Calendar, CheckCircle2, Clock, FileText, AlertTriangle } from "lucide-react";
import type { VerificationSubmission } from "../../types/verification";
import { SUBMISSION_STATUS_CONFIG } from "../../utils/status";

interface VerificationHistoryListProps {
  history: VerificationSubmission[];
  isLoading?: boolean;
}

export const VerificationHistoryList: React.FC<VerificationHistoryListProps> = ({
  history,
  isLoading = false,
}) => {
  if (isLoading) {
    return (
      <div className="p-6 text-center text-sm text-muted-foreground animate-pulse">
        Loading verification application history...
      </div>
    );
  }

  if (!history || history.length === 0) {
    return (
      <div className="p-8 text-center border rounded-xl bg-card border-border text-muted-foreground space-y-2">
        <History className="w-8 h-8 mx-auto text-muted-foreground/60" aria-hidden="true" />
        <p className="text-sm font-medium text-foreground">No historical verification applications found.</p>
        <p className="text-xs">Your prior verification review records will be preserved here.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4" aria-label="Verification Application History">
      {history.map((item, index) => {
        const config = SUBMISSION_STATUS_CONFIG[item.status] || {
          label: item.status,
          badgeClass: "bg-muted text-muted-foreground border-border",
          dotClass: "bg-muted-foreground",
        };

        const submittedDate = new Date(item.created_at).toLocaleDateString(undefined, {
          year: "numeric",
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        });

        const reviewedDate = item.reviewed_at
          ? new Date(item.reviewed_at).toLocaleDateString(undefined, {
              year: "numeric",
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })
          : null;

        return (
          <div
            key={item.id}
            className="p-5 rounded-xl border border-border bg-card shadow-xs space-y-3 hover:border-primary/40 transition-colors"
          >
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-2 border-b border-border/60">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-semibold text-muted-foreground">
                  Application #{history.length - index}
                </span>
                <span className="text-xs text-muted-foreground font-mono">({item.id.slice(0, 8)})</span>
              </div>

              <span
                className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${config.badgeClass} self-start sm:self-auto`}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${config.dotClass}`} aria-hidden="true" />
                <span>{config.label}</span>
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-muted-foreground">
              <div className="flex items-center gap-2">
                <Calendar className="w-3.5 h-3.5 text-muted-foreground/80" aria-hidden="true" />
                <span>Submitted on: <strong className="text-foreground">{submittedDate}</strong></span>
              </div>

              {reviewedDate && (
                <div className="flex items-center gap-2">
                  <Clock className="w-3.5 h-3.5 text-muted-foreground/80" aria-hidden="true" />
                  <span>Decision on: <strong className="text-foreground">{reviewedDate}</strong></span>
                </div>
              )}

              <div className="flex items-center gap-2">
                <FileText className="w-3.5 h-3.5 text-muted-foreground/80" aria-hidden="true" />
                <span>
                  Attached Evidence:{" "}
                  <strong className="text-foreground">
                    {item.documents ? item.documents.length : 0} document{item.documents?.length === 1 ? "" : "s"}
                  </strong>
                </span>
              </div>
            </div>

            {item.submission_notes && (
              <div className="p-3 rounded-lg bg-secondary/30 text-xs text-foreground space-y-1">
                <span className="font-semibold text-muted-foreground uppercase text-[10px] tracking-wider block">
                  Applicant Notes:
                </span>
                <p className="leading-relaxed">{item.submission_notes}</p>
              </div>
            )}

            {/* Rejection Reason Alert if rejected */}
            {item.status === "rejected" && item.rejection_reason && (
              <div
                className="p-3 rounded-lg bg-red-50 border border-red-200 text-xs text-red-900 space-y-1"
                role="alert"
              >
                <div className="flex items-center gap-1.5 font-bold text-red-950">
                  <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0" aria-hidden="true" />
                  <span>Administrative Rejection Rationale:</span>
                </div>
                <p className="pl-5 leading-relaxed">{item.rejection_reason}</p>
              </div>
            )}

            {/* Approved Message */}
            {item.status === "approved" && (
              <div className="flex items-center gap-2 text-xs text-emerald-800 font-medium pt-1">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" aria-hidden="true" />
                <span>Verified by administrative compliance audit. Full trading privileges granted.</span>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
