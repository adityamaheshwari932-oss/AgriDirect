import React, { useEffect, useState, useCallback } from "react";
import {
  ShieldAlert,
  Layers,
  ClipboardList,
  AlertTriangle,
  Search,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
} from "lucide-react";
import { adminApi } from "../../api/admin";
import type {
  AdminListingSummary,
  AdminListingFilterParams,
  AdminRequirementSummary,
  AdminRequirementFilterParams,
  AdminReportFilterParams,
  AdminPaymentComplaintFilterParams,
} from "../../types/admin";
import type { ReportItem } from "../../types/reports";
import type { PaymentComplaint } from "../../types/payments";
import { LoadingState, ErrorState, EmptyState } from "../../components/ui/states";
import { AdminListingModerateModal } from "../../components/admin/AdminListingModerateModal";
import { AdminRequirementModerateModal } from "../../components/admin/AdminRequirementModerateModal";
import { AdminReportModerateModal } from "../../components/admin/AdminReportModerateModal";
import { AdminDisputeModerateModal } from "../../components/admin/AdminDisputeModerateModal";

export const AdminContentModerationPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"listings" | "requirements" | "reports" | "complaints">("listings");

  // ===========================================================================
  // Tab 1: Listings State
  // ===========================================================================
  const [listings, setListings] = useState<AdminListingSummary[]>([]);
  const [listingTotal, setListingTotal] = useState(0);
  const [listingPage, setListingPage] = useState(1);
  const [listingTotalPages, setListingTotalPages] = useState(1);
  const [listingSearch, setListingSearch] = useState("");
  const [listingStatus, setListingStatus] = useState("");
  const [listingHasReports, setListingHasReports] = useState(false);
  const [listingIsDeleted, setListingIsDeleted] = useState(false);
  const [isListingLoading, setIsListingLoading] = useState(false);
  const [listingError, setListingError] = useState<string | null>(null);
  const [selectedListing, setSelectedListing] = useState<AdminListingSummary | null>(null);

  // ===========================================================================
  // Tab 2: Requirements State
  // ===========================================================================
  const [requirements, setRequirements] = useState<AdminRequirementSummary[]>([]);
  const [reqTotal, setReqTotal] = useState(0);
  const [reqPage, setReqPage] = useState(1);
  const [reqTotalPages, setReqTotalPages] = useState(1);
  const [reqSearch, setReqSearch] = useState("");
  const [reqStatus, setReqStatus] = useState("");
  const [reqHasReports, setReqHasReports] = useState(false);
  const [reqIsDeleted, setReqIsDeleted] = useState(false);
  const [isReqLoading, setIsReqLoading] = useState(false);
  const [reqError, setReqError] = useState<string | null>(null);
  const [selectedRequirement, setSelectedRequirement] = useState<AdminRequirementSummary | null>(null);

  // ===========================================================================
  // Tab 3: Safety Reports State
  // ===========================================================================
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [reportTotal, setReportTotal] = useState(0);
  const [reportPage, setReportPage] = useState(1);
  const [reportTotalPages, setReportTotalPages] = useState(1);
  const [reportStatus, setReportStatus] = useState("");
  const [reportCategory, setReportCategory] = useState("");
  const [isReportLoading, setIsReportLoading] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);
  const [selectedReport, setSelectedReport] = useState<ReportItem | null>(null);

  // ===========================================================================
  // Tab 4: Payment Complaints State
  // ===========================================================================
  const [complaints, setComplaints] = useState<PaymentComplaint[]>([]);
  const [complaintTotal, setComplaintTotal] = useState(0);
  const [complaintOffset, setComplaintOffset] = useState(0);
  const complaintLimit = 15;
  const [complaintStatus, setComplaintStatus] = useState("");
  const [isComplaintLoading, setIsComplaintLoading] = useState(false);
  const [complaintError, setComplaintError] = useState<string | null>(null);
  const [selectedComplaintId, setSelectedComplaintId] = useState<string | null>(null);

  // ===========================================================================
  // Fetch Handlers
  // ===========================================================================

  const fetchListings = useCallback(async () => {
    setIsListingLoading(true);
    setListingError(null);
    try {
      const params: AdminListingFilterParams = {
        page: listingPage,
        page_size: 15,
      };
      if (listingSearch.trim()) params.search = listingSearch.trim();
      if (listingStatus) params.status = listingStatus;
      if (listingHasReports) params.has_reports = true;
      if (listingIsDeleted) params.is_deleted = true;

      const res = await adminApi.listListings(params);
      setListings(res.items);
      setListingTotal(res.total);
      setListingTotalPages(res.total_pages || 1);
    } catch (err: unknown) {
      setListingError(err instanceof Error ? err.message : "Failed to load listings queue.");
    } finally {
      setIsListingLoading(false);
    }
  }, [listingPage, listingSearch, listingStatus, listingHasReports, listingIsDeleted]);

  const fetchRequirements = useCallback(async () => {
    setIsReqLoading(true);
    setReqError(null);
    try {
      const params: AdminRequirementFilterParams = {
        page: reqPage,
        page_size: 15,
      };
      if (reqSearch.trim()) params.search = reqSearch.trim();
      if (reqStatus) params.status = reqStatus;
      if (reqHasReports) params.has_reports = true;
      if (reqIsDeleted) params.is_deleted = true;

      const res = await adminApi.listRequirements(params);
      setRequirements(res.items);
      setReqTotal(res.total);
      setReqTotalPages(res.total_pages || 1);
    } catch (err: unknown) {
      setReqError(err instanceof Error ? err.message : "Failed to load requirements queue.");
    } finally {
      setIsReqLoading(false);
    }
  }, [reqPage, reqSearch, reqStatus, reqHasReports, reqIsDeleted]);

  const fetchReports = useCallback(async () => {
    setIsReportLoading(true);
    setReportError(null);
    try {
      const params: AdminReportFilterParams = {
        page: reportPage,
        page_size: 15,
      };
      if (reportStatus) params.status = reportStatus;
      if (reportCategory) params.category = reportCategory;

      const res = await adminApi.listReports(params);
      setReports(res.items);
      setReportTotal(res.total);
      setReportTotalPages(res.total_pages || 1);
    } catch (err: unknown) {
      setReportError(err instanceof Error ? err.message : "Failed to load safety reports.");
    } finally {
      setIsReportLoading(false);
    }
  }, [reportPage, reportStatus, reportCategory]);

  const fetchComplaints = useCallback(async () => {
    setIsComplaintLoading(true);
    setComplaintError(null);
    try {
      const params: AdminPaymentComplaintFilterParams = {
        offset: complaintOffset,
        limit: complaintLimit,
      };
      if (complaintStatus) params.status = complaintStatus;

      const res = await adminApi.listPaymentComplaints(params);
      setComplaints(res.items);
      setComplaintTotal(res.total);
    } catch (err: unknown) {
      setComplaintError(err instanceof Error ? err.message : "Failed to load payment disputes.");
    } finally {
      setIsComplaintLoading(false);
    }
  }, [complaintOffset, complaintLimit, complaintStatus]);

  // Tab change trigger
  useEffect(() => {
    if (activeTab === "listings") void fetchListings();
    else if (activeTab === "requirements") void fetchRequirements();
    else if (activeTab === "reports") void fetchReports();
    else if (activeTab === "complaints") void fetchComplaints();
  }, [activeTab, fetchListings, fetchRequirements, fetchReports, fetchComplaints]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
          <ShieldAlert className="w-6 h-6 text-primary" aria-hidden="true" />
          Platform Content & Dispute Moderation
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Catalog review, soft-deletion controls, user safety grievances, and payment dispute facilitation.
        </p>
      </div>

      {/* Tabs Bar */}
      <div className="flex items-center gap-2 border-b border-border overflow-x-auto pb-1">
        <button
          type="button"
          onClick={() => setActiveTab("listings")}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-t-xl text-xs font-semibold whitespace-nowrap transition-colors border-b-2 ${
            activeTab === "listings"
              ? "border-primary text-primary bg-primary/5"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Produce Listings</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("requirements")}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-t-xl text-xs font-semibold whitespace-nowrap transition-colors border-b-2 ${
            activeTab === "requirements"
              ? "border-primary text-primary bg-primary/5"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <ClipboardList className="w-4 h-4" />
          <span>Buyer Requirements</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("reports")}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-t-xl text-xs font-semibold whitespace-nowrap transition-colors border-b-2 ${
            activeTab === "reports"
              ? "border-primary text-primary bg-primary/5"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <ShieldAlert className="w-4 h-4" />
          <span>Safety Reports</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("complaints")}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-t-xl text-xs font-semibold whitespace-nowrap transition-colors border-b-2 ${
            activeTab === "complaints"
              ? "border-primary text-primary bg-primary/5"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <AlertTriangle className="w-4 h-4" />
          <span>Payment Complaints</span>
        </button>
      </div>

      {/* ===================================================================== */}
      {/* Tab 1: Listings Queue */}
      {/* ===================================================================== */}
      {activeTab === "listings" && (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="p-4 rounded-2xl bg-card border border-border shadow-xs flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex flex-wrap items-center gap-2 flex-1">
              <div className="relative min-w-[200px] flex-1">
                <Search className="w-3.5 h-3.5 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={listingSearch}
                  onChange={(e) => setListingSearch(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      setListingPage(1);
                      void fetchListings();
                    }
                  }}
                  placeholder="Search commodity or farmer..."
                  className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-border bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <select
                value={listingStatus}
                onChange={(e) => {
                  setListingStatus(e.target.value);
                  setListingPage(1);
                }}
                className="px-2.5 py-1.5 rounded-lg border border-border bg-card text-foreground"
              >
                <option value="">All Statuses</option>
                <option value="active">Active</option>
                <option value="closed">Closed</option>
                <option value="expired">Expired</option>
                <option value="draft">Draft</option>
              </select>

              <label className="inline-flex items-center gap-1.5 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={listingHasReports}
                  onChange={(e) => {
                    setListingHasReports(e.target.checked);
                    setListingPage(1);
                  }}
                  className="rounded border-border text-primary focus:ring-primary"
                />
                <span>Has Complaints</span>
              </label>

              <label className="inline-flex items-center gap-1.5 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={listingIsDeleted}
                  onChange={(e) => {
                    setListingIsDeleted(e.target.checked);
                    setListingPage(1);
                  }}
                  className="rounded border-border text-primary focus:ring-primary"
                />
                <span>Soft-Deleted</span>
              </label>
            </div>

            <button
              type="button"
              onClick={() => void fetchListings()}
              className="px-3 py-1.5 rounded-lg bg-secondary text-foreground hover:bg-secondary/80 font-semibold border border-border flex items-center gap-1.5 shrink-0"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Apply Filters</span>
            </button>
          </div>

          {listingError && <ErrorState message={listingError} onRetry={() => void fetchListings()} />}

          {isListingLoading ? (
            <LoadingState message="Loading produce listings queue..." />
          ) : listings.length === 0 ? (
            <EmptyState title="No listings found" description="No produce listings match the active moderation filters." />
          ) : (
            <div className="bg-card border border-border rounded-2xl shadow-xs overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-secondary/40 text-muted-foreground font-semibold border-b border-border">
                    <tr>
                      <th className="px-4 py-3">Produce & Title</th>
                      <th className="px-4 py-3">Farmer</th>
                      <th className="px-4 py-3">Quantity & Price</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">Complaints</th>
                      <th className="px-4 py-3">Expires At</th>
                      <th className="px-4 py-3 text-right">Moderation</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {listings.map((item) => (
                      <tr key={item.id} className="hover:bg-secondary/20 transition-colors">
                        <td className="px-4 py-3">
                          <div className="font-bold text-foreground">{item.product_name}</div>
                          <div className="text-[11px] text-muted-foreground truncate max-w-xs">{item.title}</div>
                          {item.is_deleted && (
                            <span className="text-[10px] text-destructive font-bold uppercase block">
                              Soft-Deleted
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <div className="font-semibold text-foreground">{item.farmer_name}</div>
                          <div className="text-[10px] text-muted-foreground font-mono">{item.farmer_email}</div>
                        </td>
                        <td className="px-4 py-3 text-muted-foreground">
                          <div>
                            <strong>{item.available_quantity}</strong> / {item.initial_quantity} {item.unit}
                          </div>
                          <div className="text-[11px] font-mono text-foreground">
                            ₹{item.price_per_unit} / {item.unit}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span className="px-2 py-0.5 rounded-full text-[11px] font-bold uppercase bg-secondary text-foreground">
                            {item.status}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          {item.reports_count > 0 ? (
                            <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/10 text-amber-700 border border-amber-500/20">
                              {item.reports_count} Complaint(s)
                            </span>
                          ) : (
                            <span className="text-muted-foreground/80 text-[11px]">0</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">
                          {new Date(item.expires_at).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            type="button"
                            onClick={() => setSelectedListing(item)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-primary hover:bg-primary/10 font-semibold transition-colors"
                          >
                            <span>Moderate</span>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {listingTotalPages > 1 && (
                <div className="px-4 py-3 border-t border-border flex items-center justify-between text-xs text-muted-foreground">
                  <span>Page {listingPage} of {listingTotalPages} ({listingTotal} listings)</span>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      disabled={listingPage <= 1}
                      onClick={() => setListingPage((p) => Math.max(1, p - 1))}
                      className="p-1.5 rounded-lg border border-border hover:bg-secondary disabled:opacity-40"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <button
                      type="button"
                      disabled={listingPage >= listingTotalPages}
                      onClick={() => setListingPage((p) => p + 1)}
                      className="p-1.5 rounded-lg border border-border hover:bg-secondary disabled:opacity-40"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ===================================================================== */}
      {/* Tab 2: Requirements Queue */}
      {/* ===================================================================== */}
      {activeTab === "requirements" && (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="p-4 rounded-2xl bg-card border border-border shadow-xs flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex flex-wrap items-center gap-2 flex-1">
              <div className="relative min-w-[200px] flex-1">
                <Search className="w-3.5 h-3.5 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={reqSearch}
                  onChange={(e) => setReqSearch(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      setReqPage(1);
                      void fetchRequirements();
                    }
                  }}
                  placeholder="Search commodity or buyer..."
                  className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-border bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <select
                value={reqStatus}
                onChange={(e) => {
                  setReqStatus(e.target.value);
                  setReqPage(1);
                }}
                className="px-2.5 py-1.5 rounded-lg border border-border bg-card text-foreground"
              >
                <option value="">All Statuses</option>
                <option value="active">Active</option>
                <option value="closed">Closed</option>
                <option value="expired">Expired</option>
                <option value="draft">Draft</option>
              </select>

              <label className="inline-flex items-center gap-1.5 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={reqHasReports}
                  onChange={(e) => {
                    setReqHasReports(e.target.checked);
                    setReqPage(1);
                  }}
                  className="rounded border-border text-primary focus:ring-primary"
                />
                <span>Has Complaints</span>
              </label>

              <label className="inline-flex items-center gap-1.5 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={reqIsDeleted}
                  onChange={(e) => {
                    setReqIsDeleted(e.target.checked);
                    setReqPage(1);
                  }}
                  className="rounded border-border text-primary focus:ring-primary"
                />
                <span>Soft-Deleted</span>
              </label>
            </div>

            <button
              type="button"
              onClick={() => void fetchRequirements()}
              className="px-3 py-1.5 rounded-lg bg-secondary text-foreground hover:bg-secondary/80 font-semibold border border-border flex items-center gap-1.5 shrink-0"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Apply Filters</span>
            </button>
          </div>

          {reqError && <ErrorState message={reqError} onRetry={() => void fetchRequirements()} />}

          {isReqLoading ? (
            <LoadingState message="Loading buyer requirements queue..." />
          ) : requirements.length === 0 ? (
            <EmptyState title="No buyer requirements found" description="No requirements match the active moderation filters." />
          ) : (
            <div className="bg-card border border-border rounded-2xl shadow-xs overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-secondary/40 text-muted-foreground font-semibold border-b border-border">
                    <tr>
                      <th className="px-4 py-3">Commodity & Title</th>
                      <th className="px-4 py-3">Buyer</th>
                      <th className="px-4 py-3">Quantity</th>
                      <th className="px-4 py-3">Condition & Date</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">Complaints</th>
                      <th className="px-4 py-3 text-right">Moderation</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {requirements.map((item) => (
                      <tr key={item.id} className="hover:bg-secondary/20 transition-colors">
                        <td className="px-4 py-3">
                          <div className="font-bold text-foreground">{item.product_name}</div>
                          <div className="text-[11px] text-muted-foreground truncate max-w-xs">{item.title}</div>
                          {item.is_deleted && (
                            <span className="text-[10px] text-destructive font-bold uppercase block">
                              Soft-Deleted
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <div className="font-semibold text-foreground">{item.buyer_name}</div>
                          <div className="text-[10px] text-muted-foreground font-mono">{item.buyer_email}</div>
                        </td>
                        <td className="px-4 py-3 text-muted-foreground">
                          <div>
                            Remaining: <strong>{item.remaining_quantity}</strong> {item.unit}
                          </div>
                          <div className="text-[10px]">Total: {item.required_quantity} {item.unit}</div>
                        </td>
                        <td className="px-4 py-3 text-muted-foreground">
                          <div className="capitalize font-semibold text-foreground">{item.price_condition}</div>
                          <div className="text-[10px]">Needed by: {item.required_by_date}</div>
                        </td>
                        <td className="px-4 py-3">
                          <span className="px-2 py-0.5 rounded-full text-[11px] font-bold uppercase bg-secondary text-foreground">
                            {item.status}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          {item.reports_count > 0 ? (
                            <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/10 text-amber-700 border border-amber-500/20">
                              {item.reports_count} Complaint(s)
                            </span>
                          ) : (
                            <span className="text-muted-foreground/80 text-[11px]">0</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            type="button"
                            onClick={() => setSelectedRequirement(item)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-primary hover:bg-primary/10 font-semibold transition-colors"
                          >
                            <span>Moderate</span>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {reqTotalPages > 1 && (
                <div className="px-4 py-3 border-t border-border flex items-center justify-between text-xs text-muted-foreground">
                  <span>Page {reqPage} of {reqTotalPages} ({reqTotal} requirements)</span>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      disabled={reqPage <= 1}
                      onClick={() => setReqPage((p) => Math.max(1, p - 1))}
                      className="p-1.5 rounded-lg border border-border hover:bg-secondary disabled:opacity-40"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <button
                      type="button"
                      disabled={reqPage >= reqTotalPages}
                      onClick={() => setReqPage((p) => p + 1)}
                      className="p-1.5 rounded-lg border border-border hover:bg-secondary disabled:opacity-40"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ===================================================================== */}
      {/* Tab 3: Safety Reports Queue */}
      {/* ===================================================================== */}
      {activeTab === "reports" && (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="p-4 rounded-2xl bg-card border border-border shadow-xs flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex flex-wrap items-center gap-2 flex-1">
              <select
                value={reportStatus}
                onChange={(e) => {
                  setReportStatus(e.target.value);
                  setReportPage(1);
                }}
                className="px-2.5 py-1.5 rounded-lg border border-border bg-card text-foreground"
              >
                <option value="">All Review Statuses</option>
                <option value="open">Open Intake</option>
                <option value="under_review">Under Review</option>
                <option value="action_taken">Action Taken</option>
                <option value="dismissed">Dismissed</option>
              </select>

              <select
                value={reportCategory}
                onChange={(e) => {
                  setReportCategory(e.target.value);
                  setReportPage(1);
                }}
                className="px-2.5 py-1.5 rounded-lg border border-border bg-card text-foreground"
              >
                <option value="">All Categories</option>
                <option value="payment">Payment Issue</option>
                <option value="quantity_mismatch">Quantity Mismatch</option>
                <option value="quality_issue">Quality Misrepresentation</option>
                <option value="fraud">Fraudulent Activity</option>
                <option value="harassment">Harassment</option>
                <option value="other">Other Concern</option>
              </select>
            </div>

            <button
              type="button"
              onClick={() => void fetchReports()}
              className="px-3 py-1.5 rounded-lg bg-secondary text-foreground hover:bg-secondary/80 font-semibold border border-border flex items-center gap-1.5 shrink-0"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh Queue</span>
            </button>
          </div>

          {reportError && <ErrorState message={reportError} onRetry={() => void fetchReports()} />}

          {isReportLoading ? (
            <LoadingState message="Loading safety reports queue..." />
          ) : reports.length === 0 ? (
            <EmptyState title="No safety reports found" description="No platform safety grievances match the current filter." />
          ) : (
            <div className="bg-card border border-border rounded-2xl shadow-xs overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-secondary/40 text-muted-foreground font-semibold border-b border-border">
                    <tr>
                      <th className="px-4 py-3">Category</th>
                      <th className="px-4 py-3">Description Narrative</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">Admin Findings</th>
                      <th className="px-4 py-3">Filed Date</th>
                      <th className="px-4 py-3 text-right">Moderation</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {reports.map((item) => (
                      <tr key={item.id} className="hover:bg-secondary/20 transition-colors">
                        <td className="px-4 py-3 font-semibold text-foreground capitalize">
                          {item.category.replace(/_/g, " ")}
                        </td>
                        <td className="px-4 py-3 max-w-sm truncate text-muted-foreground">
                          {item.description}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[11px] font-bold capitalize ${
                              item.status === "action_taken"
                                ? "bg-emerald-500/10 text-emerald-700 border border-emerald-500/20"
                                : item.status === "dismissed"
                                ? "bg-secondary text-muted-foreground"
                                : item.status === "under_review"
                                ? "bg-blue-500/10 text-blue-700 border border-blue-500/20"
                                : "bg-amber-500/10 text-amber-700 border border-amber-500/20"
                            }`}
                          >
                            {item.status.replace(/_/g, " ")}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-muted-foreground max-w-xs truncate">
                          {item.admin_notes || <span className="italic text-[11px]">Pending findings</span>}
                        </td>
                        <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">
                          {new Date(item.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            type="button"
                            onClick={() => setSelectedReport(item)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-primary hover:bg-primary/10 font-semibold transition-colors"
                          >
                            <span>Review & Moderate</span>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {reportTotalPages > 1 && (
                <div className="px-4 py-3 border-t border-border flex items-center justify-between text-xs text-muted-foreground">
                  <span>Page {reportPage} of {reportTotalPages} ({reportTotal} reports)</span>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      disabled={reportPage <= 1}
                      onClick={() => setReportPage((p) => Math.max(1, p - 1))}
                      className="p-1.5 rounded-lg border border-border hover:bg-secondary disabled:opacity-40"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <button
                      type="button"
                      disabled={reportPage >= reportTotalPages}
                      onClick={() => setReportPage((p) => p + 1)}
                      className="p-1.5 rounded-lg border border-border hover:bg-secondary disabled:opacity-40"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ===================================================================== */}
      {/* Tab 4: Payment Dispute Complaints Queue */}
      {/* ===================================================================== */}
      {activeTab === "complaints" && (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="p-4 rounded-2xl bg-card border border-border shadow-xs flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2">
              <select
                value={complaintStatus}
                onChange={(e) => {
                  setComplaintStatus(e.target.value);
                  setComplaintOffset(0);
                }}
                className="px-2.5 py-1.5 rounded-lg border border-border bg-card text-foreground"
              >
                <option value="">All Dispute Statuses</option>
                <option value="open">Open / Submitted</option>
                <option value="under_review">Under Review</option>
                <option value="resolved">Resolved</option>
                <option value="dismissed">Dismissed</option>
              </select>
            </div>

            <button
              type="button"
              onClick={() => void fetchComplaints()}
              className="px-3 py-1.5 rounded-lg bg-secondary text-foreground hover:bg-secondary/80 font-semibold border border-border flex items-center gap-1.5 shrink-0"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh Disputes</span>
            </button>
          </div>

          {complaintError && <ErrorState message={complaintError} onRetry={() => void fetchComplaints()} />}

          {isComplaintLoading ? (
            <LoadingState message="Loading payment dispute complaints..." />
          ) : complaints.length === 0 ? (
            <EmptyState title="No payment disputes found" description="No off-platform payment complaints match the filter." />
          ) : (
            <div className="bg-card border border-border rounded-2xl shadow-xs overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-secondary/40 text-muted-foreground font-semibold border-b border-border">
                    <tr>
                      <th className="px-4 py-3">Dispute Reason</th>
                      <th className="px-4 py-3">Complainant</th>
                      <th className="px-4 py-3">Evidence</th>
                      <th className="px-4 py-3">Dispute Status</th>
                      <th className="px-4 py-3">Resolution Findings</th>
                      <th className="px-4 py-3">Filed Date</th>
                      <th className="px-4 py-3 text-right">Moderation</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {complaints.map((item) => (
                      <tr key={item.id} className="hover:bg-secondary/20 transition-colors">
                        <td className="px-4 py-3 max-w-xs truncate font-semibold text-foreground">
                          {item.complaint_reason}
                        </td>
                        <td className="px-4 py-3 text-muted-foreground font-mono text-[11px]">
                          {item.complainant_user_id}
                        </td>
                        <td className="px-4 py-3">
                          {item.has_evidence ? (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-blue-800">
                              Evidence Attached
                            </span>
                          ) : (
                            <span className="text-muted-foreground/70">None</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[11px] font-bold capitalize ${
                              item.status === "resolved"
                                ? "bg-emerald-500/10 text-emerald-700 border border-emerald-500/20"
                                : item.status === "dismissed"
                                ? "bg-secondary text-muted-foreground"
                                : item.status === "under_review"
                                ? "bg-blue-500/10 text-blue-700 border border-blue-500/20"
                                : "bg-amber-500/10 text-amber-700 border border-amber-500/20"
                            }`}
                          >
                            {item.status.replace(/_/g, " ")}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-muted-foreground max-w-xs truncate">
                          {item.admin_resolution_notes || <span className="italic text-[11px]">Pending resolution</span>}
                        </td>
                        <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">
                          {new Date(item.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            type="button"
                            onClick={() => setSelectedComplaintId(item.id)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-primary hover:bg-primary/10 font-semibold transition-colors"
                          >
                            <span>Inspect & Resolve</span>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Offset Pagination */}
              {complaintTotal > complaintLimit && (
                <div className="px-4 py-3 border-t border-border flex items-center justify-between text-xs text-muted-foreground">
                  <span>
                    Showing {complaintOffset + 1}–{Math.min(complaintTotal, complaintOffset + complaintLimit)} of {complaintTotal} complaints
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      disabled={complaintOffset === 0}
                      onClick={() => setComplaintOffset((o) => Math.max(0, o - complaintLimit))}
                      className="p-1.5 rounded-lg border border-border hover:bg-secondary disabled:opacity-40"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <button
                      type="button"
                      disabled={complaintOffset + complaintLimit >= complaintTotal}
                      onClick={() => setComplaintOffset((o) => o + complaintLimit)}
                      className="p-1.5 rounded-lg border border-border hover:bg-secondary disabled:opacity-40"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ===================================================================== */}
      {/* Moderation Modals */}
      {/* ===================================================================== */}
      <AdminListingModerateModal
        listing={selectedListing}
        isOpen={Boolean(selectedListing)}
        onClose={() => setSelectedListing(null)}
        onSuccess={() => void fetchListings()}
      />

      <AdminRequirementModerateModal
        requirement={selectedRequirement}
        isOpen={Boolean(selectedRequirement)}
        onClose={() => setSelectedRequirement(null)}
        onSuccess={() => void fetchRequirements()}
      />

      <AdminReportModerateModal
        report={selectedReport}
        isOpen={Boolean(selectedReport)}
        onClose={() => setSelectedReport(null)}
        onSuccess={() => void fetchReports()}
      />

      <AdminDisputeModerateModal
        complaintId={selectedComplaintId}
        isOpen={Boolean(selectedComplaintId)}
        onClose={() => setSelectedComplaintId(null)}
        onSuccess={() => void fetchComplaints()}
      />
    </div>
  );
};

