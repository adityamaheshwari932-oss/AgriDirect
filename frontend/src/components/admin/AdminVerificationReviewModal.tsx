import React, { useEffect, useState } from "react";
import {
  X,
  ShieldCheck,
  Loader2,
  AlertCircle,
  Download,
  FileCheck,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { adminApi } from "../../api/admin";
import type { VerificationSubmission } from "../../types/verification";
import { useToast } from "../ui/toast";

interface AdminVerificationReviewModalProps {
  submissionId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const AdminVerificationReviewModal: React.FC<AdminVerificationReviewModalProps> = ({
  submissionId,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { success: toastSuccess, error: toastError } = useToast();

  const [submission, setSubmission] = useState<VerificationSubmission | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [downloadingDocId, setDownloadingDocId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Decision mode: 'review' | 'approve' | 'reject'
  const [decisionMode, setDecisionMode] = useState<"review" | "approve" | "reject">("review");
  const [approvalNotes, setApprovalNotes] = useState("");
  const [rejectionReason, setRejectionReason] = useState("");

  useEffect(() => {
    if (!isOpen || !submissionId) {
      setSubmission(null);
      setErrorMessage(null);
      setDecisionMode("review");
      return;
    }

    let isMounted = true;
    const fetchSubmission = async () => {
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const data = await adminApi.getVerification(submissionId);
        if (isMounted) {
          setSubmission(data);
          setDecisionMode("review");
          setApprovalNotes("");
          setRejectionReason("");
        }
      } catch (err: unknown) {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : "Failed to load verification submission.";
          setErrorMessage(msg);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void fetchSubmission();

    return () => {
      isMounted = false;
    };
  }, [isOpen, submissionId]);

  if (!isOpen || !submissionId) return null;

  const handleDownloadDocument = async (documentId: string, docType: string) => {
    if (!submission) return;
    setDownloadingDocId(documentId);
    try {
      const { blob, filename } = await adminApi.downloadVerificationDocument(
        submission.id,
        documentId
      );
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename || `${docType}-${documentId.slice(0, 8)}.bin`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toastSuccess("Document download initiated.", "Document Download");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to download evidence document.";
      toastError(msg, "Download Failed");
    } finally {
      setDownloadingDocId(null);
    }
  };

  const handleApprove = async () => {
    if (!submission) return;
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      await adminApi.approveVerification(submission.id, {
        approval_notes: approvalNotes.trim() || undefined,
      });
      toastSuccess("Verification application approved successfully.", "Application Approved");
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to approve verification.";
      setErrorMessage(msg);
      toastError(msg, "Approval Error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!submission) return;
    if (rejectionReason.trim().length < 3) {
      setErrorMessage("A rejection reason containing at least 3 characters is mandatory.");
      return;
    }
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      await adminApi.rejectVerification(submission.id, {
        rejection_reason: rejectionReason.trim(),
      });
      toastSuccess("Verification application rejected.", "Application Rejected");
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to reject verification.";
      setErrorMessage(msg);
      toastError(msg, "Rejection Error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const isPending = submission?.status === "pending";

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-verification-review-title"
    >
      <div className="bg-card w-full max-w-2xl rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/40">
          <div className="flex items-center gap-2.5">
            <ShieldCheck className="w-5 h-5 text-primary" aria-hidden="true" />
            <div>
              <h2 id="modal-verification-review-title" className="text-base font-bold text-foreground">
                Identity Verification Review
              </h2>
              <p className="text-[11px] text-muted-foreground">
                Administrative Credential & Document Audit
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5 max-h-[75vh] overflow-y-auto">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-12 space-y-2">
              <Loader2 className="w-7 h-7 text-primary animate-spin" />
              <p className="text-xs text-muted-foreground">Loading verification application...</p>
            </div>
          ) : errorMessage && !submission ? (
            <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span>{errorMessage}</span>
            </div>
          ) : submission ? (
            <>
              {errorMessage && (
                <div className="p-3.5 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
                  <span>{errorMessage}</span>
                </div>
              )}

              {/* Applicant Summary */}
              <div className="p-4 rounded-xl bg-secondary/30 border border-border space-y-2 text-xs">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <span className="font-bold text-foreground text-sm">
                      {submission.user_email || `User ${submission.user_id}`}
                    </span>
                    <span className="text-[11px] text-muted-foreground block font-mono">
                      ID: {submission.user_id}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-secondary text-foreground uppercase">
                      {submission.user_role || "applicant"}
                    </span>
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-xs font-semibold capitalize ${
                        submission.status === "approved"
                          ? "bg-emerald-500/10 text-emerald-700 border border-emerald-500/20"
                          : submission.status === "rejected"
                          ? "bg-rose-500/10 text-rose-700 border border-rose-500/20"
                          : "bg-blue-500/10 text-blue-700 border border-blue-500/20"
                      }`}
                    >
                      {submission.status}
                    </span>
                  </div>
                </div>

                {submission.submission_notes && (
                  <div className="pt-2 border-t border-border">
                    <span className="text-[10px] uppercase font-bold text-muted-foreground block mb-0.5">
                      Applicant Submission Notes
                    </span>
                    <p className="text-foreground">{submission.submission_notes}</p>
                  </div>
                )}
              </div>

              {/* Uploaded Documents List */}
              <div className="space-y-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                  <FileCheck className="w-3.5 h-3.5 text-primary" />
                  Attached Evidence Documents ({submission.documents.length})
                </h3>

                {submission.documents.length === 0 ? (
                  <div className="p-6 text-center rounded-xl border border-dashed border-border bg-card text-xs text-muted-foreground">
                    No documents uploaded with this submission.
                  </div>
                ) : (
                  <div className="divide-y divide-border rounded-xl border border-border bg-card overflow-hidden">
                    {submission.documents.map((doc) => (
                      <div
                        key={doc.id}
                        className="p-3.5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 text-xs"
                      >
                        <div className="space-y-0.5">
                          <span className="font-semibold text-foreground capitalize block">
                            {doc.document_type.replace(/_/g, " ")}
                          </span>
                          <div className="text-muted-foreground text-[11px] flex flex-wrap gap-x-3">
                            {doc.document_number && (
                              <span>Number: <strong className="font-mono">{doc.document_number}</strong></span>
                            )}
                            <span>Size: {(doc.file_size_bytes / 1024).toFixed(1)} KB</span>
                            <span>Type: {doc.file_mime_type}</span>
                          </div>
                        </div>

                        <button
                          type="button"
                          disabled={downloadingDocId === doc.id}
                          onClick={() => handleDownloadDocument(doc.id, doc.document_type)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-secondary text-foreground hover:bg-secondary/80 text-xs font-semibold border border-border transition-colors disabled:opacity-50 shrink-0 self-start sm:self-center"
                        >
                          {downloadingDocId === doc.id ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Download className="w-3.5 h-3.5 text-primary" />
                          )}
                          <span>Download Evidence</span>
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Rejection / Historical info */}
              {submission.rejection_reason && (
                <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 text-xs space-y-1">
                  <span className="font-bold block">Previous Rejection Reason:</span>
                  <p>{submission.rejection_reason}</p>
                </div>
              )}

              {/* Decision Workflow Modes */}
              {isPending && decisionMode === "approve" && (
                <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-50/20 space-y-3 text-xs">
                  <h4 className="font-bold text-emerald-800 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    Approve Verification Application
                  </h4>
                  <p className="text-muted-foreground">
                    This will atomically transition the user to <strong>verified</strong> status and dispatch an approval alert.
                  </p>
                  <div>
                    <label htmlFor="ver-approve-notes" className="block text-[11px] font-semibold text-foreground mb-1">
                      Approval Notes (Optional)
                    </label>
                    <textarea
                      id="ver-approve-notes"
                      rows={2}
                      value={approvalNotes}
                      onChange={(e) => setApprovalNotes(e.target.value)}
                      placeholder="Optional notes to record in audit trail..."
                      className="w-full p-2.5 text-xs rounded-xl border border-border bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                  <div className="flex items-center justify-end gap-2 pt-1">
                    <button
                      type="button"
                      onClick={() => setDecisionMode("review")}
                      disabled={isSubmitting}
                      className="px-3 py-1.5 rounded-lg border border-border bg-secondary text-foreground font-semibold"
                    >
                      Back
                    </button>
                    <button
                      type="button"
                      onClick={handleApprove}
                      disabled={isSubmitting}
                      className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-emerald-600 text-white font-semibold hover:bg-emerald-700 transition-colors shadow-xs"
                    >
                      {isSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                      <span>Confirm Approval</span>
                    </button>
                  </div>
                </div>
              )}

              {isPending && decisionMode === "reject" && (
                <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-50/20 space-y-3 text-xs">
                  <h4 className="font-bold text-rose-800 flex items-center gap-1.5">
                    <XCircle className="w-4 h-4 text-rose-600" />
                    Reject Verification Application
                  </h4>
                  <p className="text-muted-foreground">
                    This will transition the user's status to <strong>rejected</strong> and dispatch the explanation to the applicant.
                  </p>
                  <div>
                    <label htmlFor="ver-reject-reason" className="block text-[11px] font-semibold text-foreground mb-1">
                      Mandatory Rejection Reason <span className="text-destructive">*</span>
                    </label>
                    <textarea
                      id="ver-reject-reason"
                      rows={3}
                      value={rejectionReason}
                      onChange={(e) => setRejectionReason(e.target.value)}
                      placeholder="State clearly what information was missing, blurred, or invalid (minimum 3 characters)..."
                      className="w-full p-2.5 text-xs rounded-xl border border-border bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                  <div className="flex items-center justify-end gap-2 pt-1">
                    <button
                      type="button"
                      onClick={() => setDecisionMode("review")}
                      disabled={isSubmitting}
                      className="px-3 py-1.5 rounded-lg border border-border bg-secondary text-foreground font-semibold"
                    >
                      Back
                    </button>
                    <button
                      type="button"
                      onClick={handleReject}
                      disabled={isSubmitting || rejectionReason.trim().length < 3}
                      className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-destructive text-destructive-foreground font-semibold hover:bg-destructive/90 transition-colors shadow-xs disabled:opacity-40"
                    >
                      {isSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                      <span>Confirm Rejection</span>
                    </button>
                  </div>
                </div>
              )}
            </>
          ) : null}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-border flex items-center justify-between bg-secondary/20">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="px-4 py-2 rounded-xl bg-secondary text-foreground hover:bg-secondary/80 text-xs font-semibold border border-border transition-colors disabled:opacity-50"
          >
            Close
          </button>

          {isPending && decisionMode === "review" && (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setDecisionMode("reject")}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-destructive text-destructive-foreground hover:bg-destructive/90 text-xs font-semibold shadow-xs transition-colors"
              >
                <XCircle className="w-4 h-4" />
                <span>Reject Application</span>
              </button>
              <button
                type="button"
                onClick={() => setDecisionMode("approve")}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-emerald-600 text-white hover:bg-emerald-700 text-xs font-semibold shadow-xs transition-colors"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Approve Application</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

