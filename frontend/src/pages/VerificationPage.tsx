import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ShieldCheck,
  ShieldAlert,
  Clock,
  XCircle,
  Building,
  Tractor,
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  UploadCloud,
  FileCheck2,
  History,
  RotateCw,
  Loader2,
  FileText,
  AlertCircle,
} from "lucide-react";
import { useAuth } from "../store/authStore";
import { verificationApi } from "../api/verification";
import { ApiError } from "../api/errors";
import {
  SUBMISSION_STATUS_CONFIG,
  VERIFICATION_STATUS_CONFIG,
} from "../utils/status";
import type {
  VerificationDocument,
  VerificationSubmission,
} from "../types/verification";
import { VerificationDocumentUploadForm } from "../components/verification/VerificationDocumentUploadForm";
import { VerificationApplicationForm } from "../components/verification/VerificationApplicationForm";
import { VerificationDocumentsList } from "../components/verification/VerificationDocumentsList";
import { VerificationHistoryList } from "../components/verification/VerificationHistoryList";

export const VerificationPage: React.FC = () => {
  const { user, refreshUser } = useAuth();

  const [currentSubmission, setCurrentSubmission] = useState<VerificationSubmission | null>(null);
  const [history, setHistory] = useState<VerificationSubmission[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "upload" | "history">("overview");

  const isFarmer = user?.role === "farmer";
  const isBuyer = user?.role === "buyer";

  const loadVerificationData = useCallback(async () => {
    setIsLoading(true);
    setFetchError(null);

    try {
      const [submission, subHistory] = await Promise.all([
        verificationApi.getMyVerification(),
        verificationApi.getMyVerificationHistory(),
      ]);

      setCurrentSubmission(submission);
      setHistory(subHistory);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setFetchError(err.message || "Failed to load verification status. Please retry.");
      } else {
        setFetchError("Unable to reach the server. Please check your network connection.");
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user) {
      loadVerificationData();
    }
  }, [user, loadVerificationData]);

  const handleRefresh = async () => {
    try {
      await Promise.all([loadVerificationData(), refreshUser()]);
    } catch {
      // ignore refresh errors
    }
  };

  const handleUploadSuccess = async (_newDoc: VerificationDocument) => {
    try {
      await Promise.all([loadVerificationData(), refreshUser()]);
    } catch {
      // ignore refresh errors
    }
  };

  const handleSubmitSuccess = async (_newSub: VerificationSubmission) => {
    try {
      await Promise.all([loadVerificationData(), refreshUser()]);
    } catch {
      // ignore refresh errors
    }
  };

  if (!user) {
    return null;
  }

  // Unsupported roles guard
  if (!isFarmer && !isBuyer) {
    return (
      <div className="max-w-2xl mx-auto p-8 rounded-xl border border-border bg-card text-center space-y-4">
        <ShieldAlert className="w-12 h-12 text-amber-600 mx-auto" aria-hidden="true" />
        <h1 className="text-xl font-bold text-foreground">Verification Not Applicable</h1>
        <p className="text-sm text-muted-foreground">
          Identity and business verification workflows are designed exclusively for registered
          agricultural producers and commercial buyers.
        </p>
        <Link
          to="/"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary-800 transition-colors"
        >
          Return to Marketplace
        </Link>
      </div>
    );
  }

  // Verification status configuration from user object
  const statusConfig =
    VERIFICATION_STATUS_CONFIG[user.verification_status] ||
    VERIFICATION_STATUS_CONFIG.unverified;

  const isVerified = user.verification_status === "verified";
  const isPending = user.verification_status === "pending" || currentSubmission?.status === "pending";
  const isRejected = user.verification_status === "rejected" || currentSubmission?.status === "rejected";

  const getStatusIcon = () => {
    if (isVerified) {
      return <ShieldCheck className="w-8 h-8 text-emerald-600" aria-hidden="true" />;
    }
    if (isPending) {
      return <Clock className="w-8 h-8 text-blue-600" aria-hidden="true" />;
    }
    if (isRejected) {
      return <XCircle className="w-8 h-8 text-red-600" aria-hidden="true" />;
    }
    return <ShieldAlert className="w-8 h-8 text-amber-600" aria-hidden="true" />;
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8 animate-in fade-in duration-300">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-border">
        <div className="space-y-1">
          <Link
            to={isFarmer ? "/dashboard/farmer" : "/dashboard/buyer"}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:text-primary-800 transition-colors mb-1"
          >
            <ArrowLeft className="w-4 h-4" aria-hidden="true" />
            <span>Back to Dashboard</span>
          </Link>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
            Account Verification
          </h1>
          <p className="text-sm text-muted-foreground">
            {isFarmer
              ? "Validate your agricultural producer credentials to publish produce listings and conduct direct wholesale trade"
              : "Validate your commercial business entity credentials to issue trade inquiries and place direct farm orders"}
          </p>
        </div>

        <button
          type="button"
          onClick={handleRefresh}
          disabled={isLoading}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-primary self-start sm:self-auto disabled:opacity-50"
          aria-label="Refresh verification status"
        >
          <RotateCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} aria-hidden="true" />
          <span>Refresh Status</span>
        </button>
      </div>

      {/* Fetch Error Alert */}
      {fetchError && (
        <div
          className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-900 text-sm flex items-start justify-between gap-3"
          role="alert"
        >
          <div className="flex items-start gap-2.5">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
            <div className="space-y-1">
              <p className="font-semibold">Unable to Load Verification Records</p>
              <p className="text-xs text-red-800">{fetchError}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={loadVerificationData}
            className="px-3 py-1 rounded bg-red-100 hover:bg-red-200 text-red-950 font-semibold text-xs transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Section A: Current Status Card */}
      <div className="p-6 rounded-xl border border-border bg-card shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-secondary flex items-center justify-center">
              {getStatusIcon()}
            </div>
            <div>
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider block">
                Current Verification Status
              </span>
              <div className="text-xl font-bold text-foreground">
                {statusConfig.label}
              </div>
            </div>
          </div>

          <span
            className={`inline-flex items-center gap-2 px-3.5 py-1 rounded-full text-xs font-semibold border ${statusConfig.badgeClass} self-start sm:self-auto`}
          >
            <span className={`w-2 h-2 rounded-full ${statusConfig.dotClass}`} aria-hidden="true" />
            <span>Account: {statusConfig.label}</span>
          </span>
        </div>

        <div className="p-4 rounded-lg bg-secondary/50 border border-border text-sm leading-relaxed text-foreground">
          {statusConfig.description}
        </div>

        {/* Rejection Reason Notice (If rejected) */}
        {isRejected && currentSubmission?.rejection_reason && (
          <div
            className="p-4 rounded-lg bg-red-50 border border-red-200 text-sm text-red-950 space-y-1.5"
            role="alert"
          >
            <div className="flex items-center gap-2 font-bold text-red-900">
              <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0" aria-hidden="true" />
              <span>Administrative Rejection Rationale:</span>
            </div>
            <p className="pl-7 text-xs leading-relaxed text-red-800">
              {currentSubmission.rejection_reason}
            </p>
            <p className="pl-7 text-xs font-medium text-red-900 pt-1">
              You may submit a revised application or upload updated evidence documents below.
            </p>
          </div>
        )}

        {/* Verified Notice */}
        {isVerified && (
          <div className="p-4 rounded-lg bg-emerald-50 border border-emerald-200 text-sm text-emerald-950 flex items-start gap-2.5">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
            <div className="space-y-0.5">
              <p className="font-semibold text-emerald-900">Account Fully Verified</p>
              <p className="text-xs text-emerald-800">
                Your credentials have been verified by AgriDirect administrative compliance. Your
                account holds complete commercial marketplace permissions.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Navigation Tabs */}
      <div className="border-b border-border flex items-center gap-2" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "overview"}
          onClick={() => setActiveTab("overview")}
          className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "overview"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <FileCheck2 className="w-4 h-4" />
          <span>Active Application</span>
        </button>

        {!isVerified && (
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "upload"}
            onClick={() => setActiveTab("upload")}
            className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === "upload"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload Evidence</span>
          </button>
        )}

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "history"}
          onClick={() => setActiveTab("history")}
          className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "history"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <History className="w-4 h-4" />
          <span>Submission History ({history.length})</span>
        </button>
      </div>

      {/* Tab 1: Active Application & Attached Evidence */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {isLoading ? (
            <div className="p-12 text-center text-sm text-muted-foreground flex items-center justify-center gap-2">
              <Loader2 className="w-5 h-5 animate-spin text-primary" />
              <span>Loading current verification details...</span>
            </div>
          ) : currentSubmission ? (
            <div className="space-y-6">
              {/* Submission Metadata Card */}
              <div className="rounded-xl border border-border bg-card shadow-xs overflow-hidden">
                <div className="p-4 sm:p-5 bg-secondary/30 border-b border-border flex items-center justify-between">
                  <div className="flex items-center gap-2 text-foreground font-semibold text-sm">
                    <FileText className="w-4 h-4 text-primary" aria-hidden="true" />
                    <span>Application Submission #{currentSubmission.id.slice(0, 8)}</span>
                  </div>
                  {SUBMISSION_STATUS_CONFIG[currentSubmission.status] && (
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                        SUBMISSION_STATUS_CONFIG[currentSubmission.status].badgeClass
                      }`}
                    >
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${
                          SUBMISSION_STATUS_CONFIG[currentSubmission.status].dotClass
                        }`}
                        aria-hidden="true"
                      />
                      <span>{SUBMISSION_STATUS_CONFIG[currentSubmission.status].label}</span>
                    </span>
                  )}
                </div>

                <div className="p-5 sm:p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
                  <div className="space-y-1">
                    <span className="text-muted-foreground font-medium uppercase tracking-wider block">
                      Submission ID
                    </span>
                    <span className="font-mono text-foreground">{currentSubmission.id}</span>
                  </div>

                  <div className="space-y-1">
                    <span className="text-muted-foreground font-medium uppercase tracking-wider block">
                      Date Submitted
                    </span>
                    <span className="text-foreground">
                      {new Date(currentSubmission.created_at).toLocaleDateString(undefined, {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>

                  <div className="space-y-1">
                    <span className="text-muted-foreground font-medium uppercase tracking-wider block">
                      Review Date
                    </span>
                    <span className="text-foreground">
                      {currentSubmission.reviewed_at
                        ? new Date(currentSubmission.reviewed_at).toLocaleDateString(undefined, {
                            year: "numeric",
                            month: "short",
                            day: "numeric",
                          })
                        : "Pending review"}
                    </span>
                  </div>

                  <div className="space-y-1">
                    <span className="text-muted-foreground font-medium uppercase tracking-wider block">
                      Attached Documents
                    </span>
                    <span className="text-foreground font-bold">
                      {currentSubmission.documents?.length || 0} File(s)
                    </span>
                  </div>
                </div>

                {currentSubmission.submission_notes && (
                  <div className="px-5 pb-5 sm:px-6 sm:pb-6 text-xs space-y-1">
                    <span className="font-semibold text-muted-foreground uppercase text-[10px] tracking-wider block">
                      Applicant Narrative & Notes:
                    </span>
                    <p className="p-3 rounded-lg bg-secondary/30 text-foreground leading-relaxed">
                      {currentSubmission.submission_notes}
                    </p>
                  </div>
                )}
              </div>

              {/* Attached Documents */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-base font-bold text-foreground">
                    Attached Evidence Documents ({currentSubmission.documents?.length || 0})
                  </h2>
                  {!isVerified && (
                    <button
                      type="button"
                      onClick={() => setActiveTab("upload")}
                      className="text-xs font-semibold text-primary hover:text-primary-800 transition-colors"
                    >
                      + Add Another Document
                    </button>
                  )}
                </div>

                <VerificationDocumentsList documents={currentSubmission.documents || []} />
              </div>
            </div>
          ) : (
            <div className="p-8 text-center border rounded-xl bg-card border-border space-y-4">
              <div className="w-12 h-12 rounded-full bg-primary/10 text-primary mx-auto flex items-center justify-center">
                <FileText className="w-6 h-6" aria-hidden="true" />
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-bold text-foreground">No Verification Application Submitted Yet</h3>
                <p className="text-xs text-muted-foreground max-w-md mx-auto">
                  {isFarmer
                    ? "Upload your farmer identification or land ownership proof to initiate your compliance review."
                    : "Upload your business registration (GSTIN, CIN, or FSSAI license) to begin commercial verification."}
                </p>
              </div>

              <div className="pt-2 flex justify-center gap-3">
                <button
                  type="button"
                  onClick={() => setActiveTab("upload")}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary text-primary-foreground font-semibold text-sm hover:bg-primary-800 transition-colors shadow-xs"
                >
                  <UploadCloud className="w-4 h-4" />
                  <span>Upload Evidence Document</span>
                </button>
              </div>
            </div>
          )}

          {/* Acceptable Evidence Guide */}
          <div className="rounded-xl border border-border bg-card shadow-xs overflow-hidden">
            <div className="p-4 border-b border-border flex items-center gap-2">
              {isFarmer ? (
                <Tractor className="w-5 h-5 text-primary" aria-hidden="true" />
              ) : (
                <Building className="w-5 h-5 text-primary" aria-hidden="true" />
              )}
              <h3 className="text-sm font-bold text-foreground">
                {isFarmer
                  ? "Producer Verification Requirements & Accepted Evidence"
                  : "Commercial Buyer Verification Requirements & Accepted Evidence"}
              </h3>
            </div>

            <div className="p-5 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              {isFarmer ? (
                <>
                  <div className="p-3 rounded-lg bg-secondary/30 space-y-1 border border-border/60">
                    <div className="flex items-center gap-2 font-semibold text-foreground">
                      <CheckCircle2 className="w-3.5 h-3.5 text-primary" />
                      <span>Land Record / Title</span>
                    </div>
                    <p className="text-muted-foreground">7/12 extract, Patta record, or registered lease deed</p>
                  </div>

                  <div className="p-3 rounded-lg bg-secondary/30 space-y-1 border border-border/60">
                    <div className="flex items-center gap-2 font-semibold text-foreground">
                      <CheckCircle2 className="w-3.5 h-3.5 text-primary" />
                      <span>Kisan Credit Card (KCC)</span>
                    </div>
                    <p className="text-muted-foreground">Agricultural passbook or institutional farmer credit card</p>
                  </div>

                  <div className="p-3 rounded-lg bg-secondary/30 space-y-1 border border-border/60">
                    <div className="flex items-center gap-2 font-semibold text-foreground">
                      <CheckCircle2 className="w-3.5 h-3.5 text-primary" />
                      <span>Government Photo Identity</span>
                    </div>
                    <p className="text-muted-foreground">Aadhaar card, voter ID, passport, or driving license</p>
                  </div>

                  <div className="p-3 rounded-lg bg-secondary/30 space-y-1 border border-border/60">
                    <div className="flex items-center gap-2 font-semibold text-foreground">
                      <CheckCircle2 className="w-3.5 h-3.5 text-primary" />
                      <span>Organic / GAP Certificate</span>
                    </div>
                    <p className="text-muted-foreground">Accredited organic farming certification (NPOP / PGS-India)</p>
                  </div>
                </>
              ) : (
                <>
                  <div className="p-3 rounded-lg bg-secondary/30 space-y-1 border border-border/60">
                    <div className="flex items-center gap-2 font-semibold text-foreground">
                      <CheckCircle2 className="w-3.5 h-3.5 text-primary" />
                      <span>GSTIN Certificate</span>
                    </div>
                    <p className="text-muted-foreground">Goods and Services Tax Identification Number certificate</p>
                  </div>

                  <div className="p-3 rounded-lg bg-secondary/30 space-y-1 border border-border/60">
                    <div className="flex items-center gap-2 font-semibold text-foreground">
                      <CheckCircle2 className="w-3.5 h-3.5 text-primary" />
                      <span>Certificate of Incorporation</span>
                    </div>
                    <p className="text-muted-foreground">Company registration (CIN), LLP agreement, or trade license</p>
                  </div>

                  <div className="p-3 rounded-lg bg-secondary/30 space-y-1 border border-border/60">
                    <div className="flex items-center gap-2 font-semibold text-foreground">
                      <CheckCircle2 className="w-3.5 h-3.5 text-primary" />
                      <span>FSSAI License</span>
                    </div>
                    <p className="text-muted-foreground">Food safety registration for restaurants, processors, and caterers</p>
                  </div>

                  <div className="p-3 rounded-lg bg-secondary/30 space-y-1 border border-border/60">
                    <div className="flex items-center gap-2 font-semibold text-foreground">
                      <CheckCircle2 className="w-3.5 h-3.5 text-primary" />
                      <span>Commercial Entity PAN</span>
                    </div>
                    <p className="text-muted-foreground">Permanent Account Number card registered to business</p>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Upload Evidence & Submit Notes */}
      {activeTab === "upload" && !isVerified && (
        <div className="space-y-6">
          <div className="p-6 rounded-xl border border-border bg-card shadow-xs space-y-5">
            <div>
              <h2 className="text-base font-bold text-foreground">Upload Verification Evidence Document</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Attach proof documents. Uploading an evidence document will automatically initialize or attach
                to your active verification review.
              </p>
            </div>

            <VerificationDocumentUploadForm
              role={isFarmer ? "farmer" : "buyer"}
              onUploadSuccess={handleUploadSuccess}
              disabled={isVerified}
            />
          </div>

          {/* Optional Application Notes Form */}
          {!isPending && !isVerified && (
            <div className="p-6 rounded-xl border border-border bg-card shadow-xs space-y-4">
              <div>
                <h2 className="text-base font-bold text-foreground">Submit Formal Application Notes</h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Optionally provide additional operational details or harvest timelines along with your application.
                </p>
              </div>

              <VerificationApplicationForm
                role={isFarmer ? "farmer" : "buyer"}
                onSubmitSuccess={handleSubmitSuccess}
                disabled={isPending || isVerified}
              />
            </div>
          )}
        </div>
      )}

      {/* Tab 3: History */}
      {activeTab === "history" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-foreground">
              Verification Review Audit History
            </h2>
            <span className="text-xs text-muted-foreground">
              {history.length} Record{history.length === 1 ? "" : "s"}
            </span>
          </div>

          <VerificationHistoryList history={history} isLoading={isLoading} />
        </div>
      )}
    </div>
  );
};
