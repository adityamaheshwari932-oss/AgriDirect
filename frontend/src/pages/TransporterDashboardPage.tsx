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
  Search,
  UploadCloud,
  FileText,
} from "lucide-react";
import { useAuth } from "../store/authStore";
import { transportersApi } from "../api/transporters";
import { verificationApi } from "../api/verification";
import type {
  ServiceAreaCreate,
  TransporterDetail,
} from "../types/transporter";
import type { VerificationSubmission } from "../types/verification";
import {
  calculateProfileCompletion,
  getDocumentTypeLabel,
} from "../utils/status";
import { formatDate } from "../utils/formatters";

export const TransporterDashboardPage: React.FC = () => {
  const { user } = useAuth();

  const [detail, setDetail] = useState<TransporterDetail | null>(null);
  const [verificationSubmission, setVerificationSubmission] = useState<VerificationSubmission | null>(null);
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
      const [profileData, verData] = await Promise.all([
        transportersApi.getMyProfile(),
        verificationApi.getMyVerification(),
      ]);
      setDetail(profileData);
      setVerificationSubmission(verData);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load transporter profile");
    } finally {
      setLoading(false);
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
    if (!confirm("Are you sure you want to remove this service area?")) return;
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
        Access restricted to registered transportation providers.
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
          <span>{error || "Transporter profile not found."}</span>
        </div>
        <button
          onClick={fetchProfile}
          className="px-3 py-1.5 bg-destructive text-destructive-foreground rounded-lg text-xs font-semibold hover:opacity-90"
        >
          Retry
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
            className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium border ${
              user.verification_status === "verified"
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
                ? "Verified Transportation Provider"
                : user.verification_status === "pending"
                ? "Verification Under Review"
                : user.verification_status === "rejected"
                ? "Verification Rejected"
                : "Unverified Transportation Provider"}
            </span>
          </div>

          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              {detail.business_name}
            </h1>
            <p className="text-sm text-blue-200/90 mt-1">
              {detail.contact_name} &bull; {detail.phone_number} &bull; Vehicle:{" "}
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
              <span>{detail.vehicle_capacity_kg.toLocaleString()} kg Payload</span>
            </div>
            <div className="px-3 py-1.5 rounded-lg bg-white/10 backdrop-blur-xs text-xs font-medium flex items-center gap-1.5">
              <Calendar className="w-4 h-4 text-amber-300" />
              <span>{detail.experience_years} Years Exp</span>
            </div>

            {/* Availability Toggle */}
            <button
              onClick={handleToggleAvailability}
              disabled={togglingAvailability}
              className={`ms-auto px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-sm flex items-center gap-2 ${
                detail.is_available
                  ? "bg-emerald-500 hover:bg-emerald-600 text-white ring-2 ring-emerald-300/40"
                  : "bg-slate-700 hover:bg-slate-600 text-slate-200"
              }`}
            >
              <Power className="w-4 h-4" />
              <span>{detail.is_available ? "Available for Loads" : "Offline / In Transit"}</span>
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
              <span>Identity & Transport Compliance Verification</span>
            </h2>
            <p className="text-xs text-muted-foreground">
              Official verification confirms regulatory compliance, commercial roadworthiness, and permits participation in order transit.
            </p>
          </div>
          <Link
            to="/verification"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary-700 transition-colors shrink-0 shadow-xs"
          >
            <UploadCloud className="w-4 h-4" />
            <span>
              {user.verification_status === "rejected"
                ? "Resubmit Verification"
                : user.verification_status === "unverified"
                ? "Submit Verification Documents"
                : "Manage Documents"}
            </span>
          </Link>
        </div>

        {/* Profile Completion and Status Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Status Card */}
          <div className="p-4 rounded-xl bg-secondary/30 border border-border space-y-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground block">
              Current Status
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
                  ? "Not Submitted"
                  : user.verification_status === "pending"
                  ? "Under Review"
                  : user.verification_status === "verified"
                  ? "Approved & Compliant"
                  : "Rejected"}
              </span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {user.verification_status === "verified"
                ? "Full access to order transport coordination is active."
                : user.verification_status === "pending"
                ? "Submitted credentials are currently under review by platform moderation."
                : user.verification_status === "rejected"
                ? "Application was rejected. Review feedback below and resubmit."
                : "Upload vehicle RC and commercial permit to coordinate agricultural loads."}
            </p>
          </div>

          {/* Profile Completion */}
          <div className="p-4 rounded-xl bg-secondary/30 border border-border space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Profile Completeness
              </span>
              <span className="text-xs font-bold text-foreground">{completion.percentage}%</span>
            </div>
            <div className="w-full h-2 rounded-full bg-secondary overflow-hidden">
              <div
                className={`h-full transition-all duration-500 rounded-full ${
                  completion.percentage === 100
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
                ? "All recommended fleet profile information is complete."
                : `Recommended: Fill ${completion.missingFields.slice(0, 2).join(", ")}`}
            </p>
          </div>

          {/* Cycle Dates & Count */}
          <div className="p-4 rounded-xl bg-secondary/30 border border-border space-y-1 text-xs">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground block mb-1">
              Audit Timeline
            </span>
            <div className="flex justify-between py-0.5">
              <span className="text-muted-foreground">Submission Date:</span>
              <span className="font-semibold text-foreground">
                {verificationSubmission?.created_at
                  ? formatDate(verificationSubmission.created_at)
                  : "Not submitted"}
              </span>
            </div>
            <div className="flex justify-between py-0.5">
              <span className="text-muted-foreground">Last Review Date:</span>
              <span className="font-semibold text-foreground">
                {verificationSubmission?.reviewed_at
                  ? formatDate(verificationSubmission.reviewed_at)
                  : "Pending review"}
              </span>
            </div>
            <div className="flex justify-between py-0.5">
              <span className="text-muted-foreground">Evidence Files:</span>
              <span className="font-semibold text-foreground">
                {verificationSubmission?.documents?.length || 0} attached
              </span>
            </div>
          </div>
        </div>

        {/* Rejection Alert Banner if rejected */}
        {user.verification_status === "rejected" && verificationSubmission?.rejection_reason && (
          <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 text-xs space-y-2">
            <div className="flex items-center gap-2 font-bold">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>Administrative Rejection Reason</span>
            </div>
            <p className="leading-relaxed bg-white/70 p-3 rounded-lg border border-rose-200/60 font-medium">
              {verificationSubmission.rejection_reason}
            </p>
            <div className="flex items-center justify-between pt-1">
              <span className="text-rose-800">
                Please update your credentials or provide clearer documentation to resubmit.
              </span>
              <Link
                to="/verification"
                className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-semibold transition-colors shrink-0"
              >
                Resubmit Application
              </Link>
            </div>
          </div>
        )}

        {/* Submitted Documents List */}
        {verificationSubmission?.documents && verificationSubmission.documents.length > 0 && (
          <div className="space-y-3 pt-2 border-t border-border">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-primary" />
              <span>Submitted Verification Documents ({verificationSubmission.documents.length})</span>
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

      {/* Main Grid: Fleet Specs and Service Areas */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Fleet Specs */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-card border border-border rounded-xl p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h2 className="font-bold text-foreground text-sm flex items-center gap-2">
                <Truck className="w-4 h-4 text-primary" />
                <span>Vehicle & Fleet Details</span>
              </h2>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex justify-between py-1 border-b border-border/50">
                <span className="text-muted-foreground">Vehicle Type</span>
                <span className="font-semibold capitalize text-foreground">
                  {detail.transport_type.replace("_", " ")}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/50">
                <span className="text-muted-foreground">Payload Capacity</span>
                <span className="font-semibold text-foreground">
                  {detail.vehicle_capacity_kg.toLocaleString()} kg
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/50">
                <span className="text-muted-foreground">Registration No.</span>
                <span className="font-mono font-semibold text-foreground">
                  {detail.vehicle_registration_number}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/50">
                <span className="text-muted-foreground">Operating States</span>
                <span className="font-semibold text-foreground">
                  {detail.operating_states || "Not specified"}
                </span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-muted-foreground">Registered Phone</span>
                <span className="font-semibold text-foreground">{detail.phone_number}</span>
              </div>

              {detail.bio && (
                <div className="pt-2 text-xs text-muted-foreground border-t border-border">
                  <p className="font-medium text-foreground mb-1">Fleet Overview</p>
                  <p className="leading-relaxed">{detail.bio}</p>
                </div>
              )}
            </div>
          </div>

          {/* Quick Action: Find Loads Card */}
          <div className="bg-gradient-to-br from-primary/10 to-blue-500/10 border border-primary/20 rounded-xl p-5 space-y-3">
            <h3 className="font-bold text-foreground text-sm flex items-center gap-2">
              <Search className="w-4 h-4 text-primary" />
              <span>Transporter Discovery Hub</span>
            </h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Explore active agricultural marketplaces, regional harvest centers, and transport inquiries.
            </p>
            <Link
              to="/marketplace"
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary-700 transition-colors"
            >
              <span>Explore Marketplace Harvests</span>
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
                  <span>Declared Service Coverage Areas</span>
                </h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Farmers and commercial buyers will discover your fleet when booking transport within these districts.
                </p>
              </div>
              <button
                onClick={() => setShowAddArea(true)}
                className="px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary-700 transition-colors flex items-center gap-1.5 shadow-xs"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Coverage Area</span>
              </button>
            </div>

            {/* Service Areas Table / List */}
            {detail.service_areas.length === 0 ? (
              <div className="p-8 text-center border border-dashed border-border rounded-xl space-y-2">
                <MapPin className="w-8 h-8 text-muted-foreground mx-auto opacity-50" />
                <p className="text-xs font-semibold text-foreground">No service areas registered yet</p>
                <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                  Add the states and districts where your vehicles can pick up produce from farms or deliver to buyer docks.
                </p>
                <button
                  onClick={() => setShowAddArea(true)}
                  className="mt-2 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary-700 transition-colors inline-flex items-center gap-1.5"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add First Area</span>
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
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            area.coverage_type === "both"
                              ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                              : area.coverage_type === "pickup_only"
                              ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                              : "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300"
                          }`}
                        >
                          {area.coverage_type === "both"
                            ? "Pickup & Delivery"
                            : area.coverage_type === "pickup_only"
                            ? "Pickup Only"
                            : "Delivery Only"}
                        </span>
                      </div>
                      <p className="text-[11px] text-muted-foreground">
                        {area.village_town ? `${area.village_town}, ` : ""}
                        {area.pincode ? `Pincode: ${area.pincode}` : "All district pincodes"}
                      </p>
                    </div>

                    <button
                      onClick={() => handleDeleteArea(area.id)}
                      className="p-1.5 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-lg transition-colors"
                      title="Remove service area"
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
                <span>Add Service Coverage Area</span>
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
                <label className="block font-semibold text-foreground mb-1">State *</label>
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
                <label className="block font-semibold text-foreground mb-1">District *</label>
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
                    Taluka (Optional)
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
                    Pincode (Optional)
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
                <label className="block font-semibold text-foreground mb-1">Coverage Scope</label>
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
                  <option value="both">Both Pickup & Delivery</option>
                  <option value="pickup_only">Origin / Pickup Only</option>
                  <option value="delivery_only">Destination / Delivery Only</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowAddArea(false)}
                  className="px-4 py-2 rounded-lg border border-border text-foreground hover:bg-secondary font-semibold"
                  disabled={areaSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={areaSubmitting}
                  className="px-4 py-2 rounded-lg bg-primary text-primary-foreground font-semibold hover:bg-primary-700 disabled:opacity-50"
                >
                  {areaSubmitting ? "Saving..." : "Save Coverage Area"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
