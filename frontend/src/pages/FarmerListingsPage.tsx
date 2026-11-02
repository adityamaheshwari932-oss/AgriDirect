import React, { useCallback, useContext, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Plus,
  Edit,
  Trash2,
  Image as ImageIcon,
  RotateCw,
  Search,
  ShieldAlert,
  ChevronLeft,
  ChevronRight,
  MapPin,
  Calendar,
} from "lucide-react";
import { useAuth } from "../store/authStore";
import { listingsApi } from "../api/listings";
import { ApiError } from "../api/errors";
import { ToastContext } from "../components/ui/toast/ToastContext";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/states";
import { ListingCreateEditModal } from "../components/listings/ListingCreateEditModal";
import { ListingImageModal } from "../components/listings/ListingImageModal";
import { ListingDeleteModal } from "../components/listings/ListingDeleteModal";
import type {
  ProduceCategory,
  ProduceListingDetail,
} from "../types/listings";

export const FarmerListingsPage: React.FC = () => {
  const { user } = useAuth();
  const toast = useContext(ToastContext);

  const [listings, setListings] = useState<ProduceListingDetail[]>([]);
  const [categories, setCategories] = useState<ProduceCategory[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchFilter, setSearchFilter] = useState<string>("");

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals state
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingListing, setEditingListing] = useState<ProduceListingDetail | null>(null);
  const [managingPhotosListing, setManagingPhotosListing] = useState<ProduceListingDetail | null>(null);
  const [deletingListing, setDeletingListing] = useState<ProduceListingDetail | null>(null);
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

  // Load farmer listings
  const loadListings = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await listingsApi.getMyListings({
        status: statusFilter || undefined,
        page,
        page_size: pageSize,
      });
      setListings(response.items);
      setTotalCount(response.total);
      setTotalPages(response.total_pages || 1);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message || "Failed to load your produce listings.");
      } else {
        setError("Network error: Unable to reach AgriDirect servers.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, page, pageSize]);

  useEffect(() => {
    void loadListings();
  }, [loadListings]);

  // Status transitions
  const handleToggleStatus = async (
    listing: ProduceListingDetail,
    targetStatus: "active" | "draft" | "closed"
  ) => {
    try {
      const updated = await listingsApi.updateStatus(listing.id, { status: targetStatus });
      setListings((prev) => prev.map((l) => (l.id === listing.id ? updated : l)));
      toast?.success(`Listing transitioned to ${targetStatus}.`, "Status Updated");
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        toast?.error(err.message || "Status transition rejected.", "Operation Failed");
      } else {
        toast?.error("Failed to update listing status.", "Network Error");
      }
    }
  };

  // Delete listing
  const handleConfirmDelete = async () => {
    if (!deletingListing) return;
    setIsDeleting(true);
    try {
      await listingsApi.deleteListing(deletingListing.id);
      toast?.success("Listing removed and closed.", "Listing Deleted");
      setDeletingListing(null);
      void loadListings();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        toast?.error(err.message || "Failed to delete listing.", "Delete Failed");
      } else {
        toast?.error("Network error while deleting listing.", "Network Error");
      }
    } finally {
      setIsDeleting(false);
    }
  };

  const handleModalSuccess = (saved: ProduceListingDetail, isEdit: boolean) => {
    if (isEdit) {
      setListings((prev) => prev.map((l) => (l.id === saved.id ? saved : l)));
      toast?.success("Produce listing updated successfully.", "Listing Saved");
      setEditingListing(null);
    } else {
      toast?.success("New produce listing published successfully.", "Listing Published");
      setIsCreateModalOpen(false);
      void loadListings();
    }
  };

  const filteredListings = listings.filter((l) => {
    if (!searchFilter.trim()) return true;
    const q = searchFilter.toLowerCase();
    return (
      l.product_name.toLowerCase().includes(q) ||
      l.title.toLowerCase().includes(q) ||
      l.location_city?.toLowerCase().includes(q) ||
      l.location_state?.toLowerCase().includes(q)
    );
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "active":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            Active Lot
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
            Partially Sold
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
            My Produce Listings
          </h1>
          <p className="text-sm text-muted-foreground">
            Manage your harvested supply lots, wholesale pricing, and photos available to commercial buyers
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void loadListings()}
            disabled={isLoading}
            className="p-2 rounded-lg border border-border bg-card text-foreground hover:bg-secondary transition-colors disabled:opacity-50"
            aria-label="Refresh listings"
          >
            <RotateCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} aria-hidden="true" />
          </button>

          <button
            type="button"
            onClick={() => setIsCreateModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary-700 text-sm font-semibold transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" aria-hidden="true" />
            <span>Create Produce Listing</span>
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
              <p className="font-semibold text-sm">Producer Verification Incomplete</p>
              <p className="text-xs text-amber-800 leading-relaxed">
                Your account must be verified before active produce lots can be discovered by commercial buyers on the public marketplace. You can prepare drafts in the meantime.
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
            { label: "All Listings", value: "" },
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
            placeholder="Search produce name or city..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
      </div>

      {/* Content Rendering */}
      {isLoading ? (
        <LoadingState message="Loading your produce listings..." />
      ) : error ? (
        <ErrorState message={error} onRetry={() => void loadListings()} />
      ) : filteredListings.length === 0 ? (
        <EmptyState
          title={statusFilter ? `No ${statusFilter} produce listings found` : "No produce listings yet"}
          description={
            statusFilter
              ? "You do not have any produce lots matching this status filter."
              : "Publish your first farm lot to start connecting with wholesale buyers and commercial distributors."
          }
          actionLabel="Create First Listing"
          onAction={() => setIsCreateModalOpen(true)}
        />
      ) : (
        <div className="space-y-4">
          {/* Table for Desktop */}
          <div className="hidden md:block rounded-xl border border-border overflow-hidden bg-card shadow-xs">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="bg-secondary/40 text-muted-foreground font-semibold uppercase tracking-wider border-b border-border">
                <tr>
                  <th className="py-3 px-4">Produce Details</th>
                  <th className="py-3 px-4">Available Supply</th>
                  <th className="py-3 px-4">Wholesale Price</th>
                  <th className="py-3 px-4">Sourcing Location</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredListings.map((listing) => (
                  <tr key={listing.id} className="hover:bg-secondary/20 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-bold text-foreground text-sm">{listing.product_name}</div>
                      <div className="text-muted-foreground truncate max-w-xs">{listing.title}</div>
                      {listing.category?.name && (
                        <span className="inline-block mt-1 text-[10px] font-medium px-2 py-0.5 rounded bg-secondary text-foreground">
                          {listing.category.name}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-semibold text-foreground text-sm">
                        {listing.available_quantity} {listing.unit}
                      </div>
                      <div className="text-muted-foreground text-[11px]">
                        Initial: {listing.initial_quantity} {listing.unit}
                      </div>
                    </td>
                    <td className="py-3 px-4 font-semibold text-foreground text-sm">
                      ₹{Number(listing.price_per_unit).toLocaleString()} / {listing.unit}
                    </td>
                    <td className="py-3 px-4">
                      <div className="text-foreground font-medium">
                        {listing.location_city || "—"}, {listing.location_state || "—"}
                      </div>
                      {listing.harvest_date && (
                        <div className="text-muted-foreground text-[11px] flex items-center gap-1 mt-0.5">
                          <Calendar className="w-3 h-3" aria-hidden="true" />
                          Harvest: {listing.harvest_date}
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-4">{getStatusBadge(listing.status)}</td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => setManagingPhotosListing(listing)}
                          className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                          title="Manage Photos"
                          aria-label={`Manage photos for ${listing.title}`}
                        >
                          <ImageIcon className="w-4 h-4" aria-hidden="true" />
                        </button>
                        <button
                          type="button"
                          onClick={() => setEditingListing(listing)}
                          className="p-1.5 rounded-lg text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors"
                          title="Edit Details"
                          aria-label={`Edit ${listing.title}`}
                        >
                          <Edit className="w-4 h-4" aria-hidden="true" />
                        </button>
                        {listing.status === "draft" && (
                          <button
                            type="button"
                            onClick={() => handleToggleStatus(listing, "active")}
                            className="px-2 py-1 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition-colors border border-emerald-200"
                          >
                            Publish
                          </button>
                        )}
                        {listing.status === "active" && (
                          <button
                            type="button"
                            onClick={() => handleToggleStatus(listing, "closed")}
                            className="px-2 py-1 rounded text-[11px] font-semibold bg-secondary text-muted-foreground hover:text-foreground transition-colors border border-border"
                          >
                            Close
                          </button>
                        )}
                        {listing.status === "closed" && (
                          <button
                            type="button"
                            onClick={() => handleToggleStatus(listing, "active")}
                            className="px-2 py-1 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition-colors border border-emerald-200"
                          >
                            Reactivate
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => setDeletingListing(listing)}
                          className="p-1.5 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                          title="Delete Listing"
                          aria-label={`Delete ${listing.title}`}
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
            {filteredListings.map((listing) => (
              <div
                key={listing.id}
                className="p-4 rounded-xl border border-border bg-card shadow-xs space-y-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-bold text-foreground text-sm">{listing.product_name}</h3>
                    <p className="text-xs text-muted-foreground">{listing.title}</p>
                  </div>
                  {getStatusBadge(listing.status)}
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs py-2 border-y border-border">
                  <div>
                    <span className="text-muted-foreground block text-[11px]">Available Volume</span>
                    <span className="font-semibold text-foreground">
                      {listing.available_quantity} {listing.unit}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block text-[11px]">Wholesale Price</span>
                    <span className="font-semibold text-foreground">
                      ₹{Number(listing.price_per_unit).toLocaleString()} / {listing.unit}
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5" aria-hidden="true" />
                    <span>
                      {listing.location_city}, {listing.location_state}
                    </span>
                  </div>
                  <span>{listing.images?.length || 0} photos</span>
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
                  <button
                    type="button"
                    onClick={() => setManagingPhotosListing(listing)}
                    className="px-2.5 py-1.5 rounded-lg border border-border bg-card text-xs font-semibold text-foreground hover:bg-secondary flex items-center gap-1"
                  >
                    <ImageIcon className="w-3.5 h-3.5" aria-hidden="true" />
                    <span>Photos</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditingListing(listing)}
                    className="px-2.5 py-1.5 rounded-lg border border-border bg-card text-xs font-semibold text-foreground hover:bg-secondary flex items-center gap-1"
                  >
                    <Edit className="w-3.5 h-3.5" aria-hidden="true" />
                    <span>Edit</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setDeletingListing(listing)}
                    className="p-1.5 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                    aria-label="Delete listing"
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
                Showing {filteredListings.length} of {totalCount} produce listings
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
      <ListingCreateEditModal
        isOpen={isCreateModalOpen || Boolean(editingListing)}
        listingToEdit={editingListing}
        categories={categories}
        defaultState={user?.farmer_profile?.state || ""}
        defaultCity={user?.farmer_profile?.city || ""}
        onClose={() => {
          setIsCreateModalOpen(false);
          setEditingListing(null);
        }}
        onSuccess={handleModalSuccess}
      />

      {managingPhotosListing && (
        <ListingImageModal
          isOpen={Boolean(managingPhotosListing)}
          listing={managingPhotosListing}
          onClose={() => setManagingPhotosListing(null)}
          onImagesUpdated={(updatedImages) => {
            setListings((prev) =>
              prev.map((l) =>
                l.id === managingPhotosListing.id ? { ...l, images: updatedImages } : l
              )
            );
          }}
        />
      )}

      <ListingDeleteModal
        isOpen={Boolean(deletingListing)}
        listing={deletingListing}
        isDeleting={isDeleting}
        onClose={() => setDeletingListing(null)}
        onConfirm={handleConfirmDelete}
      />
    </div>
  );
};
