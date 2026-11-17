import React, { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  RotateCw,
  Search,
  ChevronLeft,
  ChevronRight,
  Handshake,
  CheckCircle2,
  Clock,
  XCircle,
  Ban,
  ArrowRight,
  Calendar,
} from "lucide-react";
import { useAuth } from "../store/authStore";
import { offersApi } from "../api/offers";
import { ApiError } from "../api/errors";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/states";
import { OfferDetailModal } from "../components/offers/OfferDetailModal";
import { formatDate, formatNumber } from "../utils/formatters";
import type { OfferStatus, OfferSummary } from "../types/offers";

export const OffersPage: React.FC = () => {
  const { t } = useTranslation(["offers", "common"]);
  const { user } = useAuth();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<"received" | "sent">("received");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchFilter, setSearchFilter] = useState<string>("");
  const [page, setPage] = useState<number>(1);
  const [pageSize] = useState<number>(10);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(1);

  const [offers, setOffers] = useState<OfferSummary[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Detail Modal
  const [selectedOfferId, setSelectedOfferId] = useState<string | null>(null);

  const loadOffers = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await offersApi.listOffers({
        role: activeTab,
        status: statusFilter || undefined,
        page,
        page_size: pageSize,
      });
      setOffers(response.items);
      setTotalCount(response.total);
      setTotalPages(response.pages || 1);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message || t("offers:load_error", "Failed to load offers."));
      } else {
        setError(t("common:errors.network", "Unable to connect to the server. Please check your network connection."));
      }
    } finally {
      setIsLoading(false);
    }
  }, [activeTab, statusFilter, page, pageSize, t]);

  useEffect(() => {
    void loadOffers();
  }, [loadOffers]);

  const filteredOffers = offers.filter((o) => {
    if (!searchFilter) return true;
    const q = searchFilter.toLowerCase();
    return (
      o.offer_number.toLowerCase().includes(q) ||
      (o.delivery_terms && o.delivery_terms.toLowerCase().includes(q))
    );
  });

  const getStatusBadge = (status: OfferStatus) => {
    switch (status) {
      case "accepted":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />
            {t("offers:status_accepted", "Accepted")}
          </span>
        );
      case "countered":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-800 border border-blue-200">
            <ArrowRight className="w-3.5 h-3.5 rtl:rotate-180" aria-hidden="true" />
            {t("offers:status_countered", "Countered")}
          </span>
        );
      case "rejected":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-50 text-red-800 border border-red-200">
            <XCircle className="w-3.5 h-3.5" aria-hidden="true" />
            {t("offers:status_rejected", "Rejected")}
          </span>
        );
      case "withdrawn":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200">
            <Ban className="w-3.5 h-3.5" aria-hidden="true" />
            {t("offers:status_withdrawn", "Withdrawn")}
          </span>
        );
      case "expired":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-800 border border-gray-300">
            <Clock className="w-3.5 h-3.5" aria-hidden="true" />
            {t("offers:status_expired", "Expired")}
          </span>
        );
      case "pending":
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/20">
            <Clock className="w-3.5 h-3.5" aria-hidden="true" />
            {t("offers:status_pending", "Pending Response")}
          </span>
        );
    }
  };

  const isVerified = user?.verification_status === "verified";

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-border">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <Handshake className="w-7 h-7 text-primary" aria-hidden="true" />
            <span>{t("offers:page_title", "Offers & Negotiations")}</span>
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {t("offers:page_subtitle", "Review commercial proposals, counter-offer terms, and finalize binding agricultural trade orders")}
          </p>
        </div>

        <button
          type="button"
          onClick={() => void loadOffers()}
          disabled={isLoading}
          className="p-2 rounded-lg border border-border bg-card text-foreground hover:bg-secondary transition-colors disabled:opacity-50 w-fit"
          title={t("common:actions.refresh", "Refresh")}
          aria-label={t("common:actions.refresh", "Refresh")}
        >
          <RotateCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} aria-hidden="true" />
        </button>
      </div>

      {/* Unverified Notice */}
      {!isVerified && (
        <div className="p-4 rounded-xl border border-amber-300 bg-amber-50 text-amber-900 text-xs flex items-start gap-3">
          <Clock className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <div className="space-y-1">
            <p className="font-bold">{t("offers:unverified_title", "Account Verification Required for Trade")}</p>
            <p className="text-amber-800">
              {t("offers:unverified_desc", "Only verified farmers and commercial buyers can finalize offers or submit counter-proposals.")}{" "}
              <Link to="/dashboard/verification" className="underline font-semibold hover:text-amber-950">
                {t("offers:unverified_link", "Complete your verification here")}
              </Link>
              .
            </p>
          </div>
        </div>
      )}

      {/* Primary Role Tabs */}
      <div className="flex border-b border-border">
        <button
          type="button"
          onClick={() => {
            setActiveTab("received");
            setPage(1);
          }}
          className={`pb-3 px-4 text-sm font-semibold transition-all border-b-2 -mb-px ${
            activeTab === "received"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          {t("offers:tabs_received", "Received Proposals")}
        </button>
        <button
          type="button"
          onClick={() => {
            setActiveTab("sent");
            setPage(1);
          }}
          className={`pb-3 px-4 text-sm font-semibold transition-all border-b-2 -mb-px ${
            activeTab === "sent"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          {t("offers:tabs_sent", "Sent Proposals")}
        </button>
      </div>

      {/* Controls Bar: Status Filter & Search */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-secondary/50 border border-border max-w-full overflow-x-auto">
          {[
            { label: t("offers:filter_all", "All Statuses"), value: "" },
            { label: t("offers:filter_pending", "Pending"), value: "pending" },
            { label: t("offers:filter_countered", "Countered"), value: "countered" },
            { label: t("offers:filter_accepted", "Accepted"), value: "accepted" },
            { label: t("offers:filter_rejected", "Rejected"), value: "rejected" },
            { label: t("offers:filter_withdrawn", "Withdrawn"), value: "withdrawn" },
          ].map((tab) => (
            <button
              key={tab.value}
              type="button"
              onClick={() => {
                setStatusFilter(tab.value);
                setPage(1);
              }}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors whitespace-nowrap shrink-0 ${
                statusFilter === tab.value
                  ? "bg-card text-foreground shadow-xs border border-border"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="relative max-w-xs w-full">
          <Search className="w-4 h-4 text-muted-foreground absolute start-3 top-2.5" aria-hidden="true" />
          <input
            type="text"
            placeholder={t("offers:search_placeholder", "Search offer number...")}
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            className="w-full ps-9 pe-3 py-1.5 text-xs rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
      </div>

      {/* Offers Content Rendering */}
      {isLoading ? (
        <LoadingState message={t("offers:loading", "Loading trade proposals...")} />
      ) : error ? (
        <ErrorState message={error} onRetry={() => void loadOffers()} />
      ) : filteredOffers.length === 0 ? (
        <EmptyState
          title={statusFilter ? t("offers:empty_filtered_title", `No ${statusFilter} offers found`) : t("offers:empty_tab_title", `No ${activeTab} proposals yet`)}
          description={
            activeTab === "received"
              ? t("offers:empty_received_desc", "You have not received any commercial trade proposals matching these filters.")
              : t("offers:empty_sent_desc", "You have not submitted any trade offers matching these filters.")
          }
          actionLabel={t("offers:browse_marketplace", "Browse Marketplace")}
          onAction={() => navigate("/marketplace")}
        />
      ) : (
        <div className="space-y-4">
          {/* Desktop Table View */}
          <div className="hidden md:block rounded-xl border border-border overflow-hidden bg-card shadow-xs">
            <table className="w-full text-start border-collapse text-xs">
              <thead className="bg-secondary/40 text-muted-foreground font-semibold uppercase tracking-wider border-b border-border">
                <tr>
                  <th className="py-3 px-4">{t("offers:th_number", "Offer Number")}</th>
                  <th className="py-3 px-4">{t("offers:th_items", "Items Summary")}</th>
                  <th className="py-3 px-4">{t("offers:th_total", "Proposal Total")}</th>
                  <th className="py-3 px-4">{t("offers:th_delivery", "Target Delivery")}</th>
                  <th className="py-3 px-4">{t("offers:th_status", "Status")}</th>
                  <th className="py-3 px-4 text-end">{t("common:labels.actions", "Actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredOffers.map((o) => (
                  <tr key={o.id} className="hover:bg-secondary/20 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-bold text-foreground text-sm">{o.offer_number}</div>
                      <div className="text-[11px] text-muted-foreground">
                        {formatDate(o.created_at)}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-semibold text-foreground">
                        {o.item_count} produce item{o.item_count > 1 ? "s" : ""}
                      </div>
                      {o.delivery_terms && (
                        <div className="text-muted-foreground truncate max-w-xs text-[11px]">
                          {o.delivery_terms}
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-4 font-bold text-foreground text-sm">
                      ₹{formatNumber(o.total_amount)}
                    </td>
                    <td className="py-3 px-4 text-muted-foreground">
                      {o.proposed_delivery_date ? (
                        <span className="flex items-center gap-1 font-medium text-foreground">
                          <Calendar className="w-3.5 h-3.5 text-muted-foreground" aria-hidden="true" />
                          {o.proposed_delivery_date}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="py-3 px-4">{getStatusBadge(o.status)}</td>
                    <td className="py-3 px-4 text-end">
                      <button
                        type="button"
                        onClick={() => setSelectedOfferId(o.id)}
                        className="px-3 py-1.5 rounded-lg border border-border bg-card text-foreground hover:bg-secondary font-semibold transition-colors shadow-xs"
                      >
                        {t("common:actions.view_details", "View Details")}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile Cards Stack */}
          <div className="grid grid-cols-1 gap-4 md:hidden">
            {filteredOffers.map((o) => (
              <div
                key={o.id}
                className="p-4 rounded-xl border border-border bg-card shadow-xs space-y-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-bold text-foreground text-sm">{o.offer_number}</h3>
                    <p className="text-[11px] text-muted-foreground">
                      Created: {formatDate(o.created_at)}
                    </p>
                  </div>
                  {getStatusBadge(o.status)}
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs pt-1 border-t border-border/60">
                  <div>
                    <span className="text-muted-foreground block text-[11px]">{t("offers:th_items", "Items")}:</span>
                    <span className="font-semibold text-foreground">
                      {o.item_count} item{o.item_count > 1 ? "s" : ""}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block text-[11px]">{t("offers:th_total", "Proposal Total")}:</span>
                    <span className="font-bold text-primary">
                      ₹{formatNumber(o.total_amount)}
                    </span>
                  </div>
                </div>

                <div className="pt-2 border-t border-border flex justify-end">
                  <button
                    type="button"
                    onClick={() => setSelectedOfferId(o.id)}
                    className="w-full py-1.5 rounded-lg border border-border bg-secondary text-foreground text-xs font-semibold hover:bg-secondary/80 transition-colors"
                  >
                    {t("common:actions.view_details", "View Details")}
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-4 border-t border-border text-xs">
              <span className="text-muted-foreground">
                {t("common:pagination.showing_results", `Showing ${filteredOffers.length} of ${totalCount} records`, {
                  count: filteredOffers.length,
                  total: totalCount,
                })}
              </span>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-1.5 rounded-lg border border-border bg-card text-foreground hover:bg-secondary disabled:opacity-40"
                  aria-label={t("common:pagination.previous", "Previous")}
                >
                  <ChevronLeft className="w-4 h-4 rtl:rotate-180" aria-hidden="true" />
                </button>
                <span className="font-semibold text-foreground px-2">
                  {t("common:pagination.showing_page", `Page ${page} of ${totalPages}`, {
                    page,
                    totalPages,
                  })}
                </span>
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="p-1.5 rounded-lg border border-border bg-card text-foreground hover:bg-secondary disabled:opacity-40"
                  aria-label={t("common:pagination.next", "Next")}
                >
                  <ChevronRight className="w-4 h-4 rtl:rotate-180" aria-hidden="true" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Offer Detail Modal */}
      <OfferDetailModal
        offerId={selectedOfferId}
        onClose={() => setSelectedOfferId(null)}
        onActionCompleted={() => {
          void loadOffers();
        }}
        onViewOrder={(orderId) => {
          navigate(`/dashboard/orders?highlight=${orderId}`);
        }}
      />
    </div>
  );
};
