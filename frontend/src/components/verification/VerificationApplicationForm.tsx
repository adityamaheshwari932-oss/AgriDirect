import React, { useState } from "react";
import { Send, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { verificationApi } from "../../api/verification";
import { ApiError } from "../../api/errors";
import type { VerificationSubmission } from "../../types/verification";

interface VerificationApplicationFormProps {
  role: "farmer" | "buyer";
  onSubmitSuccess: (submission: VerificationSubmission) => void;
  disabled?: boolean;
}

export const VerificationApplicationForm: React.FC<VerificationApplicationFormProps> = ({
  role,
  onSubmitSuccess,
  disabled = false,
}) => {
  const [submissionNotes, setSubmissionNotes] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMessage(null);

    setIsSubmitting(true);

    try {
      const submission = await verificationApi.submitVerification({
        submission_notes: submissionNotes.trim() ? submissionNotes.trim() : undefined,
        role,
      });

      setSuccessMessage("Your verification application has been submitted and is pending review.");
      setSubmissionNotes("");
      onSubmitSuccess(submission);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message || "Failed to submit verification application. Please try again.");
      } else {
        setError("A network error occurred. Please check your connection and retry.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4" aria-label="Verification Application Notes Form">
      {successMessage && (
        <div
          className="p-3.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-900 text-sm flex items-center gap-2.5"
          role="status"
        >
          <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" aria-hidden="true" />
          <span className="font-medium">{successMessage}</span>
        </div>
      )}

      {error && (
        <div
          className="p-3.5 rounded-lg bg-red-50 border border-red-200 text-red-900 text-sm flex items-start gap-2.5"
          role="alert"
        >
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <div className="flex-1 space-y-0.5">
            <p className="font-semibold">Submission Failed</p>
            <p className="text-xs text-red-800">{error}</p>
          </div>
        </div>
      )}

      <div className="space-y-1.5">
        <label htmlFor="submission-notes-input" className="block text-xs font-semibold text-foreground">
          Application Notes & Producer Narrative{" "}
          <span className="text-xs text-muted-foreground font-normal">(Optional, max 2000 characters)</span>
        </label>
        <textarea
          id="submission-notes-input"
          value={submissionNotes}
          onChange={(e) => setSubmissionNotes(e.target.value)}
          maxLength={2000}
          rows={3}
          disabled={disabled || isSubmitting}
          placeholder={
            role === "farmer"
              ? "Provide context regarding your farm operations, crop harvest cycles, acreage, or evidence details..."
              : "Provide details regarding your commercial establishment, procurement volume, receiving docks, or entity credentials..."
          }
          className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-60 disabled:cursor-not-allowed resize-y"
        />
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>Explain any special operating circumstances or certificate identifiers.</span>
          <span>{submissionNotes.length}/2000</span>
        </div>
      </div>

      <div className="flex items-center justify-end">
        <button
          type="submit"
          disabled={isSubmitting || disabled}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary text-primary-foreground font-semibold text-sm hover:bg-primary-800 transition-colors focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 disabled:cursor-not-allowed shadow-xs"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
              <span>Submitting Application...</span>
            </>
          ) : (
            <>
              <Send className="w-4 h-4" aria-hidden="true" />
              <span>Submit Formal Application</span>
            </>
          )}
        </button>
      </div>
    </form>
  );
};
