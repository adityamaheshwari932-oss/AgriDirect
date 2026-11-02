import React, { useCallback, useContext, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Plus,
  Edit,
  Trash2,
  RotateCw,
  Search,
  ShieldAlert,
  ChevronLeft,
  ChevronRight,
  MapPin,
  Calendar,
} from "lucide-react";
import { useAuth } from "../store/authStore";
import { requirementsApi } from "../api/requirements";
import { listingsApi } from "../api/listings";
import { ApiError } from "../api/errors";
import { ToastContext } from "../components/ui/toast/ToastContext";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/states";
import { RequirementCreateEditModal } from "../components/requirements/RequirementCreateEditModal";
import { RequirementDeleteModal } from "../components/requirements/RequirementDeleteModal";
import type {
  BuyerRequirementDetail,
  ProduceCategory,
} from "../types";

export const BuyerRequirementsPage: React.FC = () => {
  const { user } = useAuth();
  const toast = useContext(ToastContext);

  const [requirements, setRequirements] = useState<BuyerRequirementDetail[]>([]);
  const [categories, setCategories] = useState<ProduceCategory[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchFilter, setSearchFilter] = useState<string>("");

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingRequirement, setEditingRequirement] = useState<BuyerRequirementDetail | null>(null);
  const [deletingRequirement, setDeletingRequirement] = useState<BuyerRequirementDetail | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const isVerified = user?.verification_status === "verified";

  // Load Categories once
  useEffect(() => {
    listingsApi
      .getCategories()
      .then((cats) => setCategories(cats))
      .catch(() => {
        // Fallback silently if categories fail to load
      });
  }, []);

  // Load buyer requirements
  const loadRequirements = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await requirementsApi.getMyRequirements({
        status: statusFilter || undefined,
        page,
        page_size: pageSize,
      });
      setRequirements(response.items);
      setTotalCount(response.total);
      setTotalPages(response.total_pages || 1);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message || "Failed to load procurement requirements.");
      } else {
        setError("Network error: Unable to reach AgriDirect servers.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, page, pageSize]);

  useEffect(() => {
    void loadRequirements();
  }, [loadRequirements]);

  // Status transitions
  const handleToggleStatus = async (
    req: BuyerRequirementDetail,
    targetStatus: "active" | "draft" | "closed"
  ) => {
    try {
      const updated = await requirementsApi.updateStatus(req.id, { status: targetStatus });
      setRequirements((prev) => prev.map((r) => (r.id === req.id ? updated : r)));
      toast?.success(`Requirement transitioned to ${targetStatus}.`, "Status Updated");
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        toast?.error(err.message || "Status transition rejected.", "Operation Failed");
      } else {
        toast?.error("Failed to update requirement status.", "Network Error");
      }
    }
  };

  // Delete requirement
  const handleConfirmDelete = async () => {
    if (!deletingRequirement) return;
    setIsDeleting(true);
    try {
      await requirementsApi.deleteRequirement(deletingRequirement.id);
      toast?.success("Requirement removed and closed.", "Requirement Deleted");
      setDeletingRequirement(null);
      void loadRequirements();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        toast?.error(err.message || "Failed to delete requirement.", "Delete Failed");
      } else {
        toast?.error("Network error while deleting requirement.", "Network Error");
      }
    } finally {
      setIsDeleting(false);
    }
  };

  const handleModalSuccess = (saved: BuyerRequirementDetail, isEdit: boolean) => {
    if (isEdit) {
      setRequirements((prev) => prev.map((r) => (r.id === saved.id ? saved : r)));
      toast?.success("Procurement requirement updated successfully.", "Requirement Saved");
      setEditingRequirement(null);
    } else {
      toast?.success("New procurement demand published successfully.", "Requirement Published");
      setIsCreateModalOpen(false);
      void loadRequirements();
    }
  };

  const filteredRequirements = requirements.filter((r) => {
    if (!searchFilter.trim()) return true;
    const q = searchFilter.toLowerCase();
    return (
      r.product_name.toLowerCase().includes(q) ||
      r.title.toLowerCase().includes(q) ||
      r.destination_city?.toLowerCase().includes(q) ||
      r.destination_state?.toLowerCase().includes(q)
    );
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "active":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            Active Demand
          </span>
        );
      case "draft":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
            Draft
          </span>
        );
      case "closed":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-secondary text-muted-foreground border border-border">
            <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground" />
            Closed
          </span>
        );
      case "partially_fulfilled":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-800 border border-blue-200">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
            Partially Fulfilled
          </span>
        );
      case "fulfilled":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-50 text-purple-800 border border-purple-200">
            <span className="w-1.5 h-1.5 rounded-full bg-purple-500" />
            Fulfilled
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-secondary text-foreground border border-border">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Title & Header Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-border">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
            Buyer Requirements Board
          </h1>
          <p className="text-sm text-muted-foreground">
            Manage your commercial procurement specifications, delivery deadlines, and open demand
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void loadRequirements()}
            disabled={isLoading}
            className="p-2 rounded-lg border border-border bg-card text-foreground hover:bg-secondary transition-colors disabled:opacity-50"
            aria-label="Refresh requirements"
          >
            <RotateCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} aria-hidden="true" />
          </button>

          <button
            type="button"
            onClick={() => setIsCreateModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary-700 text-sm font-semibold transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" aria-hidden="true" />
            <span>Post Requirement</span>
          </button>
        </div>
      </div>

      {/* Unverified Warning Banner */}
      {!isVerified && (
        <div
          className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 flex items-start justify-between gap-3"
          role="alert"
        >
          <div className="flex items-start gap-3">
            <ShieldAlert className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
            <div className="space-y-1">
              <p className="font-semibold text-sm">Commercial Buyer Verification Incomplete</p>
              <p className="text-xs text-amber-800 leading-relaxed">
                Your business credentials must be verified before active procurement demands can be discovered by agricultural producers on the marketplace. You can save drafts in the meantime.
              </p>
            </div>
          </div>
          <Link
            to="/dashboard/verification"
            className="px-3 py-1.5 rounded-lg bg-amber-100 hover:bg-amber-200 text-amber-950 font-semibold text-xs whitespace-nowrap transition-colors"
          >
            Complete Verification →
          </Link>
        </div>
      )}

      {/* Filters & Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        {/* Status Tabs */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-secondary/50 border border-border w-fit">
          {[
            { label: "All Demands", value: "" },
            { label: "Active", value: "active" },
            { label: "Drafts", value: "draft" },
            { label: "Closed", value: "closed" },
          ].map((tab) => (
            <button
              key={tab.value}
              type="button"
              onClick={() => {
                setStatusFilter(tab.value);
                setPage(1);
              }}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${statusFilter === tab.value
                  ? "bg-card text-foreground shadow-xs border border-border"
                  : "text-muted-foreground hover:text-foreground"
                }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search input */}
        <div className="relative max-w-xs w-full">
          <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-2.5" aria-hidden="true" />
          <input
            type="text"
            placeholder="Search produce name or dock..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
      </div>

      {/* Content Rendering */}
      {isLoading ? (
        <LoadingState message="Loading your procurement requirements..." />
      ) : error ? (
        <ErrorState message={error} onRetry={() => void loadRequirements()} />
      ) : filteredRequirements.length === 0 ? (
        <EmptyState
          title={statusFilter ? `No ${statusFilter} requirements found` : "No procurement requirements yet"}
          description={
            statusFilter
              ? "You do not have any procurement requirements matching this filter."
              : "Post your first commercial produce requirement to invite direct supply offers from verified farmers."
          }
          actionLabel="Post First Requirement"
          onAction={() => setIsCreateModalOpen(true)}
        />
      ) : (
        <div className="space-y-4">
          {/* Table for Desktop */}
          <div className="hidden md:block rounded-xl border border-border overflow-hidden bg-card shadow-xs">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="bg-secondary/40 text-muted-foreground font-semibold uppercase tracking-wider border-b border-border">
                <tr>
                  <th className="py-3 px-4">Procurement Demand</th>
                  <th className="py-3 px-4">Required Quantity</th>
                  <th className="py-3 px-4">Pricing Term</th>
                  <th className="py-3 px-4">Destination Receiving Dock</th>
                  <th className="py-3 px-4">Deadline Date</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredRequirements.map((req) => (
                  <tr key={req.id} className="hover:bg-secondary/20 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-bold text-foreground text-sm">{req.product_name}</div>
                      <div className="text-muted-foreground truncate max-w-xs">{req.title}</div>
                      {req.category?.name && (
                        <span className="inline-block mt-1 text-[10px] font-medium px-2 py-0.5 rounded bg-secondary text-foreground">
                          {req.category.name}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-semibold text-foreground text-sm">
                        {req.remaining_quantity} {req.unit} remaining
                      </div>
                      <div className="text-muted-foreground text-[11px]">
                        Total Required: {req.required_quantity} {req.unit}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-semibold text-foreground capitalize">
                        {req.price_condition}
                      </div>
                      {req.target_price_per_unit && (
                        <div className="text-muted-foreground text-[11px]">
                          Target: ₹{Number(req.target_price_per_unit).toLocaleString()} / {req.unit}
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <div className="text-foreground font-medium">
                        {req.destination_city || "—"}, {req.destination_state || "—"}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="text-foreground font-medium flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5 text-muted-foreground" aria-hidden="true" />
                        <span>{req.required_by_date}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4">{getStatusBadge(req.status)}</td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => setEditingRequirement(req)}
                          className="p-1.5 rounded-lg text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors"
                          title="Edit Requirement"
                          aria-label={`Edit ${req.title}`}
                        >
                          <Edit className="w-4 h-4" aria-hidden="true" />
                        </button>
                        {req.status === "draft" && (
                          <button
                            type="button"
                            onClick={() => handleToggleStatus(req, "active")}
                            className="px-2 py-1 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition-colors border border-emerald-200"
                          >
                            Publish
                          </button>
                        )}
                        {req.status === "active" && (
                          <button
                            type="button"
                            onClick={() => handleToggleStatus(req, "closed")}
                            className="px-2 py-1 rounded text-[11px] font-semibold bg-secondary text-muted-foreground hover:text-foreground transition-colors border border-border"
                          >
                            Close
                          </button>
                        )}
                        {req.status === "closed" && (
                          <button
                            type="button"
                            onClick={() => handleToggleStatus(req, "active")}
                            className="px-2 py-1 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition-colors border border-emerald-200"
                          >
                            Reactivate
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => setDeletingRequirement(req)}
                          className="p-1.5 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                          title="Delete Requirement"
                          aria-label={`Delete ${req.title}`}
                        >
                          <Trash2 className="w-4 h-4" aria-hidden="true" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Cards Stack for Mobile */}
          <div className="grid grid-cols-1 gap-4 md:hidden">
            {filteredRequirements.map((req) => (
              <div
                key={req.id}
                className="p-4 rounded-xl border border-border bg-card shadow-xs space-y-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-bold text-foreground text-sm">{req.product_name}</h3>
                    <p className="text-xs text-muted-foreground">{req.title}</p>
                  </div>
                  {getStatusBadge(req.status)}
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs py-2 border-y border-border">
                  <div>
                    <span className="text-muted-foreground block text-[11px]">Remaining Demand</span>
                    <span className="font-semibold text-foreground">
                      {req.remaining_quantity} {req.unit}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block text-[11px]">Pricing Term</span>
                    <span className="font-semibold text-foreground capitalize">
                      {req.price_condition}
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5" aria-hidden="true" />
                    <span>
                      {req.destination_city}, {req.destination_state}
                    </span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5" aria-hidden="true" />
                    <span>By {req.required_by_date}</span>
                  </div>
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
                  <button
                    type="button"
                    onClick={() => setEditingRequirement(req)}
                    className="px-2.5 py-1.5 rounded-lg border border-border bg-card text-xs font-semibold text-foreground hover:bg-secondary flex items-center gap-1"
                  >
                    <Edit className="w-3.5 h-3.5" aria-hidden="true" />
                    <span>Edit</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setDeletingRequirement(req)}
                    className="p-1.5 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                    aria-label="Delete requirement"
                  >
                    <Trash2 className="w-4 h-4" aria-hidden="true" />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-4 border-t border-border text-xs text-muted-foreground">
              <span>
                Showing {filteredRequirements.length} of {totalCount} procurement requirements
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border bg-card hover:bg-secondary disabled:opacity-50 transition-colors"
                >
                  <ChevronLeft className="w-3.5 h-3.5" aria-hidden="true" />
                  <span>Previous</span>
                </button>
                <span className="font-semibold text-foreground">
                  Page {page} of {totalPages}
                </span>
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border bg-card hover:bg-secondary disabled:opacity-50 transition-colors"
                >
                  <span>Next</span>
                  <ChevronRight className="w-3.5 h-3.5" aria-hidden="true" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Modals */}
      <RequirementCreateEditModal
        isOpen={isCreateModalOpen || Boolean(editingRequirement)}
        requirementToEdit={editingRequirement}
        categories={categories}
        defaultState={user?.buyer_profile?.state || ""}
        defaultCity={user?.buyer_profile?.city || ""}
        onClose={() => {
          setIsCreateModalOpen(false);
          setEditingRequirement(null);
        }}
        onSuccess={handleModalSuccess}
      />

      <RequirementDeleteModal
        isOpen={Boolean(deletingRequirement)}
        requirement={deletingRequirement}
        isDeleting={isDeleting}
        onClose={() => setDeletingRequirement(null)}
        onConfirm={handleConfirmDelete}
      />
    </div>
  );
};
