import React, { useEffect, useState } from "react";
import {
  X,
  User as UserIcon,
  Shield,
  Loader2,
  AlertCircle,
  Activity,
  History,
  Tractor,
  Store,
} from "lucide-react";
import { adminApi } from "../../api/admin";
import type { AdminUserDetail } from "../../types/admin";

interface AdminUserDetailModalProps {
  userId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export const AdminUserDetailModal: React.FC<AdminUserDetailModalProps> = ({
  userId,
  isOpen,
  onClose,
}) => {
  const [detail, setDetail] = useState<AdminUserDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !userId) {
      setDetail(null);
      setError(null);
      return;
    }

    let isMounted = true;
    const fetchDetail = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await adminApi.getUserDetail(userId);
        if (isMounted) {
          setDetail(data);
        }
      } catch (err: unknown) {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : "Failed to load user details.";
          setError(msg);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void fetchDetail();

    return () => {
      isMounted = false;
    };
  }, [isOpen, userId]);

  if (!isOpen || !userId) return null;

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case "active":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-700 border border-emerald-500/20">
            Active
          </span>
        );
      case "restricted":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-700 border border-amber-500/20">
            Restricted
          </span>
        );
      case "suspended":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-500/10 text-red-700 border border-red-500/20">
            Suspended
          </span>
        );
      case "blocked":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-destructive text-destructive-foreground">
            Blocked
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-secondary text-foreground capitalize">
            {status}
          </span>
        );
    }
  };

  const renderVerificationBadge = (status: string) => {
    switch (status) {
      case "verified":
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
            Verified
          </span>
        );
      case "pending":
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-blue-100 text-blue-800 border border-blue-200">
            Pending Review
          </span>
        );
      case "rejected":
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-rose-100 text-rose-800 border border-rose-200">
            Rejected
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-secondary text-muted-foreground">
            Unverified
          </span>
        );
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-user-detail-title"
    >
      <div className="bg-card w-full max-w-2xl rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/40">
          <div className="flex items-center gap-2.5">
            <UserIcon className="w-5 h-5 text-primary" aria-hidden="true" />
            <div>
              <h2 id="modal-user-detail-title" className="text-base font-bold text-foreground">
                User Inspection Details
              </h2>
              <p className="text-[11px] text-muted-foreground">
                Comprehensive Account Profile & Governance History
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

        {/* Content */}
        <div className="p-6 space-y-6 max-h-[75vh] overflow-y-auto">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-12 space-y-2">
              <Loader2 className="w-8 h-8 text-primary animate-spin" />
              <p className="text-xs text-muted-foreground">Loading user inspection profile...</p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span>{error}</span>
            </div>
          ) : detail ? (
            <>
              {/* Account Summary Header Card */}
              <div className="p-4 rounded-xl bg-secondary/30 border border-border space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                      {detail.email}
                      <span className="text-[11px] font-semibold uppercase px-2 py-0.5 rounded bg-secondary text-foreground">
                        {detail.role}
                      </span>
                    </h3>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      User ID: <span className="font-mono">{detail.id}</span>
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {renderStatusBadge(detail.account_status)}
                    {renderVerificationBadge(detail.verification_status)}
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-border text-xs">
                  <div>
                    <span className="text-[10px] text-muted-foreground block">Phone</span>
                    <span className="font-medium text-foreground">{detail.phone_number || "None"}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-muted-foreground block">Registered</span>
                    <span className="font-medium text-foreground">
                      {new Date(detail.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-muted-foreground block">Last Updated</span>
                    <span className="font-medium text-foreground">
                      {new Date(detail.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-muted-foreground block">Role</span>
                    <span className="font-semibold text-foreground capitalize">{detail.role}</span>
                  </div>
                </div>
              </div>

              {/* Activity Counts */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5 text-primary" />
                  Platform Activity Metrics
                </h4>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                  <div className="p-3 rounded-lg border border-border bg-card text-center">
                    <span className="text-lg font-bold text-foreground block">
                      {detail.activity_counts.listings_count}
                    </span>
                    <span className="text-[10px] text-muted-foreground">Listings</span>
                  </div>
                  <div className="p-3 rounded-lg border border-border bg-card text-center">
                    <span className="text-lg font-bold text-foreground block">
                      {detail.activity_counts.requirements_count}
                    </span>
                    <span className="text-[10px] text-muted-foreground">Requirements</span>
                  </div>
                  <div className="p-3 rounded-lg border border-border bg-card text-center">
                    <span className="text-lg font-bold text-foreground block">
                      {detail.activity_counts.completed_orders_count}
                    </span>
                    <span className="text-[10px] text-muted-foreground">Completed Orders</span>
                  </div>
                  <div className="p-3 rounded-lg border border-border bg-card text-center">
                    <span className="text-lg font-bold text-foreground block">
                      {detail.activity_counts.reports_filed_count}
                    </span>
                    <span className="text-[10px] text-muted-foreground">Reports Filed</span>
                  </div>
                  <div className="p-3 rounded-lg border border-border bg-card text-center">
                    <span className="text-lg font-bold text-foreground block">
                      {detail.activity_counts.reports_received_count}
                    </span>
                    <span className="text-[10px] text-muted-foreground">Reports Received</span>
                  </div>
                </div>
              </div>

              {/* Role Profile Details */}
              {detail.farmer_profile && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                    <Tractor className="w-3.5 h-3.5 text-primary" />
                    Farmer Agricultural Profile
                  </h4>
                  <div className="p-4 rounded-xl border border-border bg-card space-y-2 text-xs">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      <div>
                        <span className="text-[10px] text-muted-foreground block">Full Name</span>
                        <span className="font-semibold text-foreground">{detail.farmer_profile.full_name}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-muted-foreground block">Farm Name</span>
                        <span className="font-semibold text-foreground">{detail.farmer_profile.farm_name}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-muted-foreground block">Location Address</span>
                        <span className="text-foreground">{detail.farmer_profile.farm_location_address}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-muted-foreground block">City / State / Postal</span>
                        <span className="text-foreground">
                          {detail.farmer_profile.city}, {detail.farmer_profile.state} {detail.farmer_profile.postal_code}
                        </span>
                      </div>
                      {detail.farmer_profile.farm_size_acres && (
                        <div>
                          <span className="text-[10px] text-muted-foreground block">Farm Size</span>
                          <span className="text-foreground">{detail.farmer_profile.farm_size_acres} Acres</span>
                        </div>
                      )}
                      {detail.farmer_profile.primary_crops && (
                        <div>
                          <span className="text-[10px] text-muted-foreground block">Primary Crops</span>
                          <span className="text-foreground">{detail.farmer_profile.primary_crops}</span>
                        </div>
                      )}
                    </div>
                    {detail.farmer_profile.farming_practices && (
                      <div className="pt-2 border-t border-border">
                        <span className="text-[10px] text-muted-foreground block">Farming Practices</span>
                        <p className="text-foreground">{detail.farmer_profile.farming_practices}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {detail.buyer_profile && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                    <Store className="w-3.5 h-3.5 text-primary" />
                    Commercial Buyer Profile
                  </h4>
                  <div className="p-4 rounded-xl border border-border bg-card space-y-2 text-xs">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      <div>
                        <span className="text-[10px] text-muted-foreground block">Contact Person</span>
                        <span className="font-semibold text-foreground">{detail.buyer_profile.contact_person_name}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-muted-foreground block">Business Name</span>
                        <span className="font-semibold text-foreground">{detail.buyer_profile.business_name}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-muted-foreground block">Business Type</span>
                        <span className="text-foreground">{detail.buyer_profile.business_type}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-muted-foreground block">Registration Number</span>
                        <span className="font-mono text-foreground">
                          {detail.buyer_profile.business_registration_number || "Not provided"}
                        </span>
                      </div>
                      <div className="sm:col-span-2">
                        <span className="text-[10px] text-muted-foreground block">Receiving Address</span>
                        <span className="text-foreground">
                          {detail.buyer_profile.delivery_receiving_address}, {detail.buyer_profile.city},{" "}
                          {detail.buyer_profile.state} {detail.buyer_profile.postal_code}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Verification Summary */}
              {detail.verification_summary && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                    <Shield className="w-3.5 h-3.5 text-primary" />
                    Latest Identity Verification Summary
                  </h4>
                  <div className="p-3.5 rounded-xl border border-border bg-card text-xs space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Submission Status:</span>
                      <span className="font-semibold capitalize text-foreground">
                        {detail.verification_summary.status || "None"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Uploaded Documents:</span>
                      <span className="font-semibold text-foreground">
                        {detail.verification_summary.documents_count} file(s)
                      </span>
                    </div>
                    {detail.verification_summary.submitted_at && (
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">Submitted At:</span>
                        <span className="text-foreground">
                          {new Date(detail.verification_summary.submitted_at).toLocaleString()}
                        </span>
                      </div>
                    )}
                    {detail.verification_summary.rejection_reason && (
                      <div className="pt-2 border-t border-border text-rose-700 bg-rose-50/50 p-2 rounded">
                        <span className="font-semibold block">Rejection Rationale:</span>
                        <p>{detail.verification_summary.rejection_reason}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Recent Audit Logs */}
              {detail.recent_audit_logs.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                    <History className="w-3.5 h-3.5 text-primary" />
                    Recent Governance Audit Trail
                  </h4>
                  <div className="rounded-xl border border-border divide-y divide-border overflow-hidden bg-card text-xs">
                    {detail.recent_audit_logs.map((log) => (
                      <div key={log.id} className="p-3 space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-foreground">{log.action}</span>
                          <span className="text-[11px] text-muted-foreground">
                            {new Date(log.created_at).toLocaleString()}
                          </span>
                        </div>
                        {log.reason && (
                          <p className="text-muted-foreground italic">"{log.reason}"</p>
                        )}
                        <div className="text-[10px] text-muted-foreground/80 flex items-center gap-2">
                          <span>Admin: {log.admin_user_id}</span>
                          {log.ip_address && <span>• IP: {log.ip_address}</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : null}
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

