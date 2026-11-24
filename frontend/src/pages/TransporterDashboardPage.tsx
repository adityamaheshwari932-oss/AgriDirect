import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Truck,
  MapPin,
  ShieldCheck,
  ShieldAlert,
  Clock,
  XCircle,
  Plus,
  Trash2,
  Weight,
  Calendar,
  AlertCircle,
  CheckCircle2,
  Power,
  RefreshCw,
  UploadCloud,
  FileText,
  ClipboardList,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../store/authStore";
import { transportersApi } from "../api/transporters";
import { verificationApi } from "../api/verification";
import type {
  ServiceAreaCreate,
  TransporterDetail,
  TransportConnectionRequest,
} from "../types/transporter";
import type { VerificationSubmission } from "../types/verification";
import {
  calculateProfileCompletion,
  getDocumentTypeLabel,
} from "../utils/status";
import { formatDate, formatNumber } from "../utils/formatters";

export const TransporterDashboardPage: React.FC = () => {
  const { t } = useTranslation(["delivery", "common"]);
  const { user } = useAuth();

  const [detail, setDetail] = useState<TransporterDetail | null>(null);
  const [verificationSubmission, setVerificationSubmission] = useState<VerificationSubmission | null>(null);
  const [incomingRequests, setIncomingRequests] = useState<TransportConnectionRequest[]>([]);
  const [requestFilter, setRequestFilter] = useState<"all" | "pending" | "accepted" | "declined">("all");
  const [respondingRequestId, setRespondingRequestId] = useState<string | null>(null);
  const [decliningRequestId, setDecliningRequestId] = useState<string | null>(null);
  const [responseText, setResponseText] = useState("");
  const [rejectionReason, setRejectionReason] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Service Area Form Modal State
  const [showAddArea, setShowAddArea] = useState(false);
  const [areaForm, setAreaForm] = useState<ServiceAreaCreate>({
    state: "",
    district: "",
    taluka_subdistrict: "",
    pincode: "",
    coverage_type: "both",
    is_active: true,
  });
  const [areaSubmitting, setAreaSubmitting] = useState(false);
  const [areaError, setAreaError] = useState<string | null>(null);

  // Availability toggle loading
  const [togglingAvailability, setTogglingAvailability] = useState(false);

  const fetchProfile = async () => {
    try {
      setLoading(true);
      setError(null);
      const [profileData, verData, reqsData] = await Promise.all([
        transportersApi.getMyProfile(),
        verificationApi.getMyVerification(),
        transportersApi.listConnectionRequests().catch(() => ({ total: 0, items: [] })),
      ]);
      setDetail(profileData);
      setVerificationSubmission(verData);
      setIncomingRequests(reqsData.items || []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load transporter profile");
    } finally {
      setLoading(false);
    }
  };

  const handleAcceptRequest = async (requestId: string, notes?: string) => {
    try {
      setActionLoading(true);
      const updated = await transportersApi.acceptConnectionRequest(requestId, {
        response_notes: notes || undefined,
      });
      setIncomingRequests((prev) =>
        prev.map((r) => (r.id === requestId ? updated : r))
      );
      setRespondingRequestId(null);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to accept request");
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeclineRequest = async (requestId: string, reason: string, notes?: string) => {
    try {
      setActionLoading(true);
      const updated = await transportersApi.declineConnectionRequest(requestId, {
        rejection_reason: reason,
        response_notes: notes || undefined,
      });
      setIncomingRequests((prev) =>
        prev.map((r) => (r.id === requestId ? updated : r))
      );
      setDecliningRequestId(null);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to decline request");
    } finally {
      setActionLoading(false);
    }
  };

  useEffect(() => {
    if (user?.role === "transporter") {
      fetchProfile();
    }
  }, [user]);

  const handleToggleAvailability = async () => {
    if (!detail || togglingAvailability) return;
    try {
      setTogglingAvailability(true);
      const updated = await transportersApi.updateMyProfile({
        is_available: !detail.is_available,
      });
      setDetail((prev) => (prev ? { ...prev, is_available: updated.is_available } : null));
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to toggle availability");
    } finally {
      setTogglingAvailability(false);
    }
  };

  const handleAddArea = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!areaForm.state.trim() || !areaForm.district.trim()) {
      setAreaError("State and District are required.");
      return;
    }
    try {
      setAreaSubmitting(true);
      setAreaError(null);
      const newArea = await transportersApi.addServiceArea({
        state: areaForm.state.trim(),
        district: areaForm.district.trim(),
        taluka_subdistrict: areaForm.taluka_subdistrict?.trim() || undefined,
        pincode: areaForm.pincode?.trim() || undefined,
        coverage_type: areaForm.coverage_type,
        is_active: true,
      });
      setDetail((prev) =>
        prev ? { ...prev, service_areas: [...prev.service_areas, newArea] } : null
      );
      setShowAddArea(false);
      setAreaForm({
        state: "",
        district: "",
        taluka_subdistrict: "",
        pincode: "",
        coverage_type: "both",
        is_active: true,
      });
    } catch (err: unknown) {
      setAreaError(err instanceof Error ? err.message : "Failed to add service area");
    } finally {
      setAreaSubmitting(false);
    }
  };

  const handleDeleteArea = async (areaId: string) => {
    if (!confirm(t("delivery:confirm_remove_service_area", "Are you sure you want to remove this service area?"))) return;
    try {
      await transportersApi.deleteServiceArea(areaId);
      setDetail((prev) =>
        prev
          ? {
            ...prev,
            service_areas: prev.service_areas.filter((a) => a.id !== areaId),
          }
          : null
      );
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to delete service area");
    }
  };

  if (!user || user.role !== "transporter") {
    return (
      <div className="p-8 text-center text-muted-foreground">
        {t("delivery:dashboard_restricted", "Access restricted to registered transportation providers.")}
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-16">
        <RefreshCw className="w-8 h-8 text-primary animate-spin" />
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="p-6 bg-destructive/10 border border-destructive/20 rounded-xl text-destructive text-sm flex items-center justify-between">
        <div className="flex items-center gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error || t("delivery:profile_not_found", "Transporter profile not found.")}</span>
        </div>
        <button
          onClick={fetchProfile}
          className="px-3 py-1.5 bg-destructive text-destructive-foreground rounded-lg text-xs font-semibold hover:opacity-90"
        >
          {t("delivery:retry", "Retry")}
        </button>
      </div>
    );
  }

  const completion = user
    ? calculateProfileCompletion(user)
    : { percentage: 0, completedCount: 0, totalCount: 1, missingFields: [] };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Top Welcome Banner */}
      <div className="p-6 sm:p-8 rounded-2xl bg-gradient-to-r from-blue-900 via-indigo-900 to-slate-900 text-white shadow-md relative overflow-hidden">
        <div className="absolute end-0 bottom-0 rtl:-translate-x-8 translate-x-8 translate-y-8 opacity-10 pointer-events-none">
          <Truck className="w-64 h-64" aria-hidden="true" />
        </div>

        <div className="relative z-10 max-w-3xl space-y-4">
          <div
            className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium border ${user.verification_status === "verified"
              ? "bg-emerald-950/80 border-emerald-600/60 text-emerald-300"
              : user.verification_status === "pending"
                ? "bg-blue-950/80 border-blue-600/60 text-blue-300"
                : user.verification_status === "rejected"
                  ? "bg-rose-950/80 border-rose-600/60 text-rose-300"
                  : "bg-amber-950/80 border-amber-600/60 text-amber-300"
              }`}
          >
            {user.verification_status === "verified" ? (
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
            ) : user.verification_status === "pending" ? (
              <Clock className="w-4 h-4 text-blue-400" />
            ) : user.verification_status === "rejected" ? (
              <XCircle className="w-4 h-4 text-rose-400" />
            ) : (
              <ShieldAlert className="w-4 h-4 text-amber-400" />
            )}
            <span>
              {user.verification_status === "verified"
                ? t("delivery:verified_provider", "Verified Transportation Provider")
                : user.verification_status === "pending"
                  ? t("delivery:under_review", "Verification Under Review")
                  : user.verification_status === "rejected"
                    ? t("delivery:rejected_provider", "Verification Rejected")
                    : t("delivery:unverified_provider", "Unverified Transportation Provider")}
            </span>
          </div>

          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              {detail.business_name}
            </h1>
            <p className="text-sm text-blue-200/90 mt-1">
              {detail.contact_name} &bull; {detail.phone_number} &bull; {t("delivery:vehicle_colon", "Vehicle:")}{" "}
              <span className="font-mono">{detail.vehicle_registration_number}</span>
            </p>
          </div>

          {/* Quick specs pill bar */}
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <div className="px-3 py-1.5 rounded-lg bg-white/10 backdrop-blur-xs text-xs font-medium flex items-center gap-1.5">
              <Truck className="w-4 h-4 text-blue-300" />
              <span className="capitalize">{detail.transport_type.replace("_", " ")}</span>
            </div>
            <div className="px-3 py-1.5 rounded-lg bg-white/10 backdrop-blur-xs text-xs font-medium flex items-center gap-1.5">
              <Weight className="w-4 h-4 text-emerald-300" />
              <span>{t("delivery:payload_kg", "{{weight}} kg Payload", { weight: detail.vehicle_capacity_kg.toLocaleString() })}</span>
            </div>
            <div className="px-3 py-1.5 rounded-lg bg-white/10 backdrop-blur-xs text-xs font-medium flex items-center gap-1.5">
              <Calendar className="w-4 h-4 text-amber-300" />
              <span>{t("delivery:years_exp_count", "{{count}} Years Exp", { count: detail.experience_years })}</span>
            </div>

            {/* Availability Toggle */}
            <button
              onClick={handleToggleAvailability}
              disabled={togglingAvailability}
              className={`ms-auto px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-sm flex items-center gap-2 ${detail.is_available
                ? "bg-emerald-500 hover:bg-emerald-600 text-white ring-2 ring-emerald-300/40"
                : "bg-slate-700 hover:bg-slate-600 text-slate-200"
                }`}
            >
              <Power className="w-4 h-4" />
              <span>{detail.is_available ? t("delivery:available_for_loads", "Available for Loads") : t("delivery:offline_in_transit", "Offline / In Transit")}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Dedicated Verification & Compliance Section */}
      <div className="bg-card border border-border rounded-2xl p-6 shadow-xs space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-4">
          <div className="space-y-1">
            <h2 className="text-base sm:text-lg font-bold text-foreground flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-primary" />
              <span>{t("delivery:compliance_title", "Identity & Transport Compliance Verification")}</span>
            </h2>
            <p className="text-xs text-muted-foreground">
              {t("delivery:compliance_desc", "Official verification confirms regulatory compliance, commercial roadworthiness, and permits participation in order transit.")}
            </p>
          </div>
          <Link
            to="/dashboard/verification"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary-700 transition-colors shrink-0 shadow-xs"
          >
            <UploadCloud className="w-4 h-4" />
            <span>
              {user.verification_status === "rejected"
                ? t("delivery:resubmit_verification", "Resubmit Verification")
                : user.verification_status === "unverified"
                  ? t("delivery:submit_verification", "Submit Verification Documents")
                  : t("delivery:manage_documents", "Manage Documents")}
            </span>
          </Link>
        </div>

        {/* Profile Completion and Status Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Status Card */}
          <div className="p-4 rounded-xl bg-secondary/30 border border-border space-y-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground block">
              {t("delivery:current_status", "Current Status")}
            </span>
            <div className="flex items-center gap-2">
              {user.verification_status === "verified" ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              ) : user.verification_status === "pending" ? (
                <Clock className="w-5 h-5 text-blue-600" />
              ) : user.verification_status === "rejected" ? (
                <XCircle className="w-5 h-5 text-rose-600" />
              ) : (
                <ShieldAlert className="w-5 h-5 text-amber-600" />
              )}
              <span className="text-sm font-bold text-foreground capitalize">
                {user.verification_status === "unverified"
                  ? t("delivery:status_not_submitted", "Not Submitted")
                  : user.verification_status === "pending"
                    ? t("delivery:status_under_review", "Under Review")
                    : user.verification_status === "verified"
                      ? t("delivery:status_approved_compliant", "Approved & Compliant")
                      : t("delivery:status_rejected", "Rejected")}
              </span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {user.verification_status === "verified"
                ? t("delivery:status_desc_verified", "Full access to order transport coordination is active.")
                : user.verification_status === "pending"
                  ? t("delivery:status_desc_pending", "Submitted credentials are currently under review by platform moderation.")
                  : user.verification_status === "rejected"
                    ? t("delivery:status_desc_rejected", "Application was rejected. Review feedback below and resubmit.")
                    : t("delivery:status_desc_unverified", "Upload vehicle RC and commercial permit to coordinate agricultural loads.")}
            </p>
          </div>

          {/* Profile Completion */}
          <div className="p-4 rounded-xl bg-secondary/30 border border-border space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                {t("delivery:profile_completeness", "Profile Completeness")}
              </span>
              <span className="text-xs font-bold text-foreground">{completion.percentage}%</span>
            </div>
            <div className="w-full h-2 rounded-full bg-secondary overflow-hidden">
              <div
                className={`h-full transition-all duration-500 rounded-full ${completion.percentage === 100
                  ? "bg-emerald-500"
                  : completion.percentage > 60
                    ? "bg-primary"
                    : "bg-amber-500"
                  }`}
                style={{ width: `${completion.percentage}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              {completion.missingFields.length === 0
                ? t("delivery:profile_complete_msg", "All recommended fleet profile information is complete.")
                : t("delivery:profile_recommended_fill", "Recommended: Fill {{fields}}", { fields: completion.missingFields.slice(0, 2).join(", ") })}
            </p>
          </div>

          {/* Cycle Dates & Count */}
          <div className="p-4 rounded-xl bg-secondary/30 border border-border space-y-1 text-xs">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground block mb-1">
              {t("delivery:audit_timeline", "Audit Timeline")}
            </span>
            <div className="flex justify-between py-0.5">
              <span className="text-muted-foreground">{t("delivery:submission_date", "Submission Date:")}</span>
              <span className="font-semibold text-foreground">
                {verificationSubmission?.created_at
                  ? formatDate(verificationSubmission.created_at)
                  : t("delivery:not_submitted", "Not submitted")}
              </span>
            </div>
            <div className="flex justify-between py-0.5">
              <span className="text-muted-foreground">{t("delivery:last_review_date", "Last Review Date:")}</span>
              <span className="font-semibold text-foreground">
                {verificationSubmission?.reviewed_at
                  ? formatDate(verificationSubmission.reviewed_at)
                  : t("delivery:pending_review", "Pending review")}
              </span>
            </div>
            <div className="flex justify-between py-0.5">
              <span className="text-muted-foreground">{t("delivery:evidence_files", "Evidence Files:")}</span>
              <span className="font-semibold text-foreground">
                {t("delivery:attached_count", "{{count}} attached", { count: verificationSubmission?.documents?.length || 0 })}
              </span>
            </div>
          </div>
        </div>

        {/* Rejection Alert Banner if rejected */}
        {user.verification_status === "rejected" && verificationSubmission?.rejection_reason && (
          <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 text-xs space-y-2">
            <div className="flex items-center gap-2 font-bold">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{t("delivery:admin_rejection_reason", "Administrative Rejection Reason")}</span>
            </div>
            <p className="leading-relaxed bg-white/70 p-3 rounded-lg border border-rose-200/60 font-medium">
              {verificationSubmission.rejection_reason}
            </p>
            <div className="flex items-center justify-between pt-1">
              <span className="text-rose-800">
                {t("delivery:resubmit_notice", "Please update your credentials or provide clearer documentation to resubmit.")}
              </span>
              <Link
                to="/dashboard/verification"
                className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-semibold transition-colors shrink-0"
              >
                {t("delivery:resubmit_application", "Resubmit Application")}
              </Link>
            </div>
          </div>
        )}

        {/* Submitted Documents List */}
        {verificationSubmission?.documents && verificationSubmission.documents.length > 0 && (
          <div className="space-y-3 pt-2 border-t border-border">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-primary" />
              <span>{t("delivery:submitted_verification_docs", "Submitted Verification Documents ({{count}})", { count: verificationSubmission.documents.length })}</span>
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {verificationSubmission.documents.map((doc) => (
                <div
                  key={doc.id}
                  className="p-3.5 rounded-xl border border-border bg-card flex items-center justify-between gap-2 text-xs"
                >
                  <div className="space-y-0.5 overflow-hidden">
                    <span className="font-semibold text-foreground block truncate">
                      {getDocumentTypeLabel(doc.document_type)}
                    </span>
                    <span className="text-[11px] text-muted-foreground block">
                      {(doc.file_size_bytes / 1024).toFixed(1)} KB &bull; {formatDate(doc.created_at)}
                    </span>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-secondary text-foreground uppercase shrink-0">
                    {verificationSubmission.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Incoming Service Requests & Active Cargo Connections */}
      <div className="bg-card border border-border rounded-xl p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border pb-4">
          <div>
            <h2 className="font-bold text-foreground text-sm flex items-center gap-2">
              <Truck className="w-4 h-4 text-primary" />
              <span>{t("delivery:service_requests_title", "Transportation Service Requests & Active Cargo")}</span>
              <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-primary/10 text-primary">
                {incomingRequests.length}
              </span>
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              {t("delivery:service_requests_desc", "Review and coordinate freight haulage requests directly with farmers and commercial buyers.")}
            </p>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
            {(["all", "pending", "accepted", "declined"] as const).map((status) => {
              const count =
                status === "all"
                  ? incomingRequests.length
                  : incomingRequests.filter((r) => r.status === status).length;
              return (
                <button
                  key={status}
                  type="button"
                  onClick={() => setRequestFilter(status)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-semibold capitalize transition-colors flex items-center gap-1.5 whitespace-nowrap ${requestFilter === status
                    ? "bg-primary text-primary-foreground shadow-xs"
                    : "bg-secondary/60 text-muted-foreground hover:bg-secondary hover:text-foreground"
                    }`}
                >
                  <span>
                    {status === "all"
                      ? t("delivery:filter_all", "All")
                      : status === "pending"
                        ? t("delivery:filter_pending", "Pending")
                        : status === "accepted"
                          ? t("delivery:filter_accepted", "Accepted")
                          : t("delivery:filter_declined", "Declined")}
                  </span>
                  <span
                    className={`px-1.5 py-0.2 rounded-full text-[10px] ${requestFilter === status
                      ? "bg-white/20 text-white"
                      : "bg-background text-foreground"
                      }`}
                  >
                    {count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Request List or Empty State */}
        {(() => {
          const filtered = incomingRequests.filter(
            (r) => requestFilter === "all" || r.status === requestFilter
          );

          if (filtered.length === 0) {
            return (
              <div className="text-center py-8 px-4 rounded-xl border border-dashed border-border bg-secondary/10">
                <Truck className="w-8 h-8 text-muted-foreground/50 mx-auto mb-2" />
                <p className="text-sm font-semibold text-foreground">
                  {t("delivery:no_requests_found", "No {{status}} requests found", {
                    status: requestFilter !== "all" ? requestFilter : "",
                  })}
                </p>
                <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
                  {t("delivery:no_requests_hint", "When farmers or buyers request your haulage services for active deals, their requests will appear here.")}
                </p>
              </div>
            );
          }

          return (
            <div className="space-y-3">
              {filtered.map((req) => (
                <div
                  key={req.id}
                  className="p-4 rounded-xl border border-border bg-card/50 hover:bg-card transition-all space-y-3"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-sm text-foreground">
                        {req.requester_name || t("delivery:procurement_counterparty", "Procurement Counterparty")}
                      </span>
                      {req.requester_role && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-secondary text-secondary-foreground uppercase">
                          {req.requester_role}
                        </span>
                      )}
                      {req.order_id && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                          {t("delivery:order_num_badge", "Order #{{id}}", { id: req.order_id.slice(0, 8) })}
                        </span>
                      )}
                      {req.offer_id && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300">
                          {t("delivery:offer_num_badge", "Offer #{{id}}", { id: req.offer_id.slice(0, 8) })}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <span
                        className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold capitalize ${req.status === "accepted"
                          ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                          : req.status === "declined"
                            ? "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300"
                            : req.status === "cancelled"
                              ? "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300"
                              : "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                          }`}
                      >
                        {req.status}
                      </span>
                      <span className="text-[11px] text-muted-foreground">
                        {formatDate(req.created_at)}
                      </span>
                    </div>
                  </div>

                  {/* Route & Cargo Grid */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2.5 text-xs bg-secondary/30 p-3 rounded-lg border border-border/40">
                    <div>
                      <span className="text-[10px] text-muted-foreground uppercase font-semibold block">{t("delivery:pickup_location", "Pickup Location")}</span>
                      <p className="font-medium text-foreground truncate mt-0.5">
                        {req.pickup_district && req.pickup_state
                          ? `${req.pickup_district}, ${req.pickup_state}`
                          : req.pickup_state || t("delivery:as_negotiated", "As negotiated")}
                      </p>
                      {req.pickup_address && (
                        <p className="text-[11px] text-muted-foreground truncate">{req.pickup_address}</p>
                      )}
                    </div>

                    <div>
                      <span className="text-[10px] text-muted-foreground uppercase font-semibold block">{t("delivery:delivery_destination", "Delivery Destination")}</span>
                      <p className="font-medium text-foreground truncate mt-0.5">
                        {req.delivery_district && req.delivery_state
                          ? `${req.delivery_district}, ${req.delivery_state}`
                          : req.delivery_state || t("delivery:as_negotiated", "As negotiated")}
                      </p>
                      {req.delivery_address && (
                        <p className="text-[11px] text-muted-foreground truncate">{req.delivery_address}</p>
                      )}
                    </div>

                    <div>
                      <span className="text-[10px] text-muted-foreground uppercase font-semibold block">{t("delivery:cargo_weight_label", "Cargo & Weight")}</span>
                      <p className="font-medium text-foreground truncate mt-0.5">
                        {req.cargo_description || t("delivery:produce_freight", "Produce freight")}
                      </p>
                      <p className="text-[11px] text-muted-foreground">
                        {req.weight_kg ? `${formatNumber(req.weight_kg)} kg` : t("delivery:custom_weight", "Custom weight")}
                      </p>
                    </div>

                    <div>
                      <span className="text-[10px] text-muted-foreground uppercase font-semibold block">{t("delivery:required_schedule", "Required Schedule")}</span>
                      <p className="font-medium text-foreground mt-0.5">
                        {req.required_delivery_date || t("delivery:flexible_immediate", "Flexible / Immediate")}
                      </p>
                    </div>
                  </div>

                  {req.notes && (
                    <div className="text-xs text-muted-foreground bg-muted/30 px-3 py-2 rounded-lg border border-border/40">
                      <span className="font-semibold text-foreground">{t("delivery:requester_notes", "Requester Notes: ")}</span>
                      {req.notes}
                    </div>
                  )}

                  {req.response_notes && (
                    <div className="text-xs text-muted-foreground bg-emerald-500/5 px-3 py-2 rounded-lg border border-emerald-500/20">
                      <span className="font-semibold text-emerald-700 dark:text-emerald-400">{t("delivery:your_response", "Your Response: ")}</span>
                      {req.response_notes}
                    </div>
                  )}

                  {req.rejection_reason && (
                    <div className="text-xs text-muted-foreground bg-rose-500/5 px-3 py-2 rounded-lg border border-rose-500/20">
                      <span className="font-semibold text-rose-700 dark:text-rose-400">{t("delivery:decline_reason", "Decline Reason: ")}</span>
                      {req.rejection_reason}
                    </div>
                  )}

                  {/* Actions for Pending Requests */}
                  {req.status === "pending" && (
                    <div className="pt-2 border-t border-border flex flex-col gap-2">
                      {respondingRequestId === req.id ? (
                        <div className="p-3 rounded-lg border border-emerald-500/30 bg-emerald-50/50 dark:bg-emerald-950/20 space-y-2">
                          <label className="text-xs font-semibold text-foreground block">
                            {t("delivery:acceptance_msg_label", "Acceptance Message / Loading Instructions (Optional):")}
                          </label>
                          <textarea
                            value={responseText}
                            onChange={(e) => setResponseText(e.target.value)}
                            placeholder={t("delivery:acceptance_msg_placeholder", "e.g. Can dispatch vehicle tomorrow 8 AM. Driver will call before arrival.")}
                            className="w-full text-xs p-2 rounded border border-border bg-background focus:ring-1 focus:ring-primary outline-hidden"
                            rows={2}
                          />
                          <div className="flex items-center justify-end gap-2">
                            <button
                              type="button"
                              onClick={() => {
                                setRespondingRequestId(null);
                                setResponseText("");
                              }}
                              className="px-3 py-1.5 rounded text-xs font-medium text-muted-foreground hover:bg-secondary"
                            >
                              {t("common:actions.cancel", "Cancel")}
                            </button>
                            <button
                              type="button"
                              disabled={actionLoading}
                              onClick={() => handleAcceptRequest(req.id, responseText)}
                              className="px-3 py-1.5 rounded text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white transition-colors"
                            >
                              {actionLoading ? t("delivery:accepting", "Accepting...") : t("delivery:confirm_acceptance", "Confirm Acceptance")}
                            </button>
                          </div>
                        </div>
                      ) : decliningRequestId === req.id ? (
                        <div className="p-3 rounded-lg border border-rose-500/30 bg-rose-50/50 dark:bg-rose-950/20 space-y-2">
                          <label className="text-xs font-semibold text-foreground block">
                            {t("delivery:decline_reason_label", "Decline Reason (Required):")}
                          </label>
                          <input
                            type="text"
                            value={rejectionReason}
                            onChange={(e) => setRejectionReason(e.target.value)}
                            placeholder={t("delivery:decline_reason_placeholder", "e.g. Vehicle already fully booked on requested date.")}
                            className="w-full text-xs p-2 rounded border border-border bg-background focus:ring-1 focus:ring-rose-500 outline-hidden"
                          />
                          <div className="flex items-center justify-end gap-2">
                            <button
                              type="button"
                              onClick={() => {
                                setDecliningRequestId(null);
                                setRejectionReason("");
                              }}
                              className="px-3 py-1.5 rounded text-xs font-medium text-muted-foreground hover:bg-secondary"
                            >
                              {t("common:actions.cancel", "Cancel")}
                            </button>
                            <button
                              type="button"
                              disabled={actionLoading || !rejectionReason.trim()}
                              onClick={() => handleDeclineRequest(req.id, rejectionReason, responseText)}
                              className="px-3 py-1.5 rounded text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white transition-colors disabled:opacity-50"
                            >
                              {actionLoading ? t("delivery:declining", "Declining...") : t("delivery:confirm_decline", "Confirm Decline")}
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-center justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              setDecliningRequestId(req.id);
                              setRespondingRequestId(null);
                              setRejectionReason("");
                            }}
                            className="px-3 py-1.5 rounded-lg text-xs font-semibold border border-rose-300 dark:border-rose-800 text-rose-700 dark:text-rose-300 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors"
                          >
                            {t("delivery:decline_request", "Decline Request")}
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setRespondingRequestId(req.id);
                              setDecliningRequestId(null);
                              setResponseText("");
                            }}
                            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white transition-colors"
                          >
                            {t("delivery:accept_request", "Accept Request")}
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          );
        })()}
      </div>

      {/* Main Grid: Fleet Specs and Service Areas */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Fleet Specs */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-card border border-border rounded-xl p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h2 className="font-bold text-foreground text-sm flex items-center gap-2">
                <Truck className="w-4 h-4 text-primary" />
                <span>{t("delivery:fleet_details_title", "Vehicle & Fleet Details")}</span>
              </h2>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex justify-between py-1 border-b border-border/50">
                <span className="text-muted-foreground">{t("delivery:vehicle_type", "Vehicle Type")}</span>
                <span className="font-semibold capitalize text-foreground">
                  {detail.transport_type.replace("_", " ")}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/50">
                <span className="text-muted-foreground">{t("delivery:payload_capacity", "Payload Capacity")}</span>
                <span className="font-semibold text-foreground">
                  {detail.vehicle_capacity_kg.toLocaleString()} kg
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/50">
                <span className="text-muted-foreground">{t("delivery:registration_no", "Registration No.")}</span>
                <span className="font-mono font-semibold text-foreground">
                  {detail.vehicle_registration_number}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/50">
                <span className="text-muted-foreground">{t("delivery:operating_states", "Operating States")}</span>
                <span className="font-semibold text-foreground">
                  {detail.operating_states || t("delivery:not_specified", "Not specified")}
                </span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-muted-foreground">{t("delivery:phone_number", "Registered Phone")}</span>
                <span className="font-semibold text-foreground">{detail.phone_number}</span>
              </div>

              {detail.bio && (
                <div className="pt-2 text-xs text-muted-foreground border-t border-border">
                  <p className="font-medium text-foreground mb-1">{t("delivery:fleet_overview", "Fleet Overview")}</p>
                  <p className="leading-relaxed">{detail.bio}</p>
                </div>
              )}
            </div>
          </div>

          {/* Quick Action: Active Transport Deliveries */}
          <div className="bg-gradient-to-br from-primary/10 to-blue-500/10 border border-primary/20 rounded-xl p-5 space-y-3">
            <h3 className="font-bold text-foreground text-sm flex items-center gap-2">
              <ClipboardList className="w-4 h-4 text-primary" />
              <span>{t("delivery:assigned_deliveries_title", "Assigned Transit Deliveries")}</span>
            </h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {t("delivery:assigned_deliveries_desc", "Review active agricultural transit assignments, cargo manifests, and delivery status updates.")}
            </p>
            <Link
              to="/dashboard/orders"
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary-700 transition-colors"
            >
              <span>{t("delivery:view_transport_orders", "View Transport Orders")}</span>
            </Link>
          </div>
        </div>

        {/* Right Column: Service Area Coverage */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-card border border-border rounded-xl p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div>
                <h2 className="font-bold text-foreground text-sm flex items-center gap-2">
                  <MapPin className="w-4 h-4 text-emerald-600" />
                  <span>{t("delivery:service_coverage_title", "Declared Service Coverage Areas")}</span>
                </h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {t("delivery:service_coverage_desc", "Farmers and commercial buyers will discover your fleet when booking transport within these districts.")}
                </p>
              </div>
              <button
                onClick={() => setShowAddArea(true)}
                className="px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary-700 transition-colors flex items-center gap-1.5 shadow-xs"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>{t("delivery:add_coverage_area", "Add Coverage Area")}</span>
              </button>
            </div>

            {/* Service Areas Table / List */}
            {detail.service_areas.length === 0 ? (
              <div className="p-8 text-center border border-dashed border-border rounded-xl space-y-2">
                <MapPin className="w-8 h-8 text-muted-foreground mx-auto opacity-50" />
                <p className="text-xs font-semibold text-foreground">{t("delivery:no_service_areas_registered", "No service areas registered yet")}</p>
                <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                  {t("delivery:no_service_areas_prompt", "Add the states and districts where your vehicles can pick up produce from farms or deliver to buyer docks.")}
                </p>
                <button
                  onClick={() => setShowAddArea(true)}
                  className="mt-2 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary-700 transition-colors inline-flex items-center gap-1.5"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>{t("delivery:add_first_area", "Add First Area")}</span>
                </button>
              </div>
            ) : (
              <div className="divide-y divide-border/60">
                {detail.service_areas.map((area) => (
                  <div
                    key={area.id}
                    className="py-3 flex items-center justify-between gap-4 hover:bg-secondary/40 px-2 rounded-lg transition-colors"
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-xs text-foreground">
                          {area.state} &bull; {area.district}
                        </span>
                        {area.taluka_subdistrict && (
                          <span className="text-muted-foreground text-xs">
                            ({area.taluka_subdistrict})
                          </span>
                        )}
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${area.coverage_type === "both"
                            ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                            : area.coverage_type === "pickup_only"
                              ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                              : "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300"
                            }`}
                        >
                          {area.coverage_type === "both"
                            ? t("delivery:pickup_and_delivery", "Pickup & Delivery")
                            : area.coverage_type === "pickup_only"
                              ? t("delivery:pickup_only", "Pickup Only")
                              : t("delivery:delivery_only", "Delivery Only")}
                        </span>
                      </div>
                      <p className="text-[11px] text-muted-foreground">
                        {area.village_town ? `${area.village_town}, ` : ""}
                        {area.pincode ? `Pincode: ${area.pincode}` : t("delivery:all_district_pincodes", "All district pincodes")}
                      </p>
                    </div>

                    <button
                      onClick={() => handleDeleteArea(area.id)}
                      className="p-1.5 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-lg transition-colors"
                      title={t("delivery:remove_service_area", "Remove service area")}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Add Service Area Modal */}
      {showAddArea && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-card border border-border rounded-2xl max-w-md w-full p-6 shadow-xl space-y-5 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="font-bold text-sm text-foreground flex items-center gap-2">
                <Plus className="w-4 h-4 text-primary" />
                <span>{t("delivery:add_coverage_area_modal_title", "Add Service Coverage Area")}</span>
              </h3>
              <button
                onClick={() => setShowAddArea(false)}
                className="text-muted-foreground hover:text-foreground text-xs"
              >
                ✕
              </button>
            </div>

            {areaError && (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg text-xs text-destructive flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{areaError}</span>
              </div>
            )}

            <form onSubmit={handleAddArea} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-foreground mb-1">{t("delivery:state_required", "State *")}</label>
                <input
                  type="text"
                  value={areaForm.state}
                  onChange={(e) => setAreaForm({ ...areaForm, state: e.target.value })}
                  placeholder="e.g. Maharashtra"
                  className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary outline-none"
                  required
                />
              </div>

              <div>
                <label className="block font-semibold text-foreground mb-1">{t("delivery:district_required", "District *")}</label>
                <input
                  type="text"
                  value={areaForm.district}
                  onChange={(e) => setAreaForm({ ...areaForm, district: e.target.value })}
                  placeholder="e.g. Pune"
                  className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary outline-none"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-foreground mb-1">
                    {t("delivery:taluka_optional", "Taluka (Optional)")}
                  </label>
                  <input
                    type="text"
                    value={areaForm.taluka_subdistrict}
                    onChange={(e) =>
                      setAreaForm({ ...areaForm, taluka_subdistrict: e.target.value })
                    }
                    placeholder="e.g. Haveli"
                    className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary outline-none"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-foreground mb-1">
                    {t("delivery:pincode_optional", "Pincode (Optional)")}
                  </label>
                  <input
                    type="text"
                    value={areaForm.pincode}
                    onChange={(e) => setAreaForm({ ...areaForm, pincode: e.target.value })}
                    placeholder="e.g. 411028"
                    className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-foreground mb-1">{t("delivery:coverage_scope", "Coverage Scope")}</label>
                <select
                  value={areaForm.coverage_type}
                  onChange={(e) =>
                    setAreaForm({
                      ...areaForm,
                      coverage_type: e.target.value as "pickup_only" | "delivery_only" | "both",
                    })
                  }
                  className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary outline-none"
                >
                  <option value="both">{t("delivery:scope_both", "Both Pickup & Delivery")}</option>
                  <option value="pickup_only">{t("delivery:scope_pickup", "Origin / Pickup Only")}</option>
                  <option value="delivery_only">{t("delivery:scope_delivery", "Destination / Delivery Only")}</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowAddArea(false)}
                  className="px-4 py-2 rounded-lg border border-border text-foreground hover:bg-secondary font-semibold"
                  disabled={areaSubmitting}
                >
                  {t("common:actions.cancel", "Cancel")}
                </button>
                <button
                  type="submit"
                  disabled={areaSubmitting}
                  className="px-4 py-2 rounded-lg bg-primary text-primary-foreground font-semibold hover:bg-primary-700 disabled:opacity-50"
                >
                  {areaSubmitting ? t("delivery:saving", "Saving...") : t("delivery:save_coverage_area", "Save Coverage Area")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
