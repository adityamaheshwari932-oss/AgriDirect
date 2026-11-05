import React, { useCallback, useEffect, useState } from "react";
import {
  RotateCw,
  Search,
  ChevronLeft,
  ChevronRight,
  Eye,
  Clock,
  CheckCircle2,
  XCircle,
  ShoppingBag,
  Printer,
} from "lucide-react";
import { ordersApi } from "../api/orders";
import { useAuth } from "../store/authStore";
import type { OrderListItem } from "../types/orders";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/states";
import { OrderDetailModal } from "../components/orders/OrderDetailModal";

export const OrdersPage: React.FC = () => {
  const { user } = useAuth();

  const [orders, setOrders] = useState<OrderListItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(1);

  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Detail Modal
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);

  const loadOrders = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await ordersApi.listOrders({
        status: statusFilter || undefined,
        page,
        page_size: pageSize,
      });
      setOrders(response.items || []);
      setTotalCount(response.total);
      setTotalPages(response.total_pages || 1);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load orders.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, page, pageSize]);

  useEffect(() => {
    void loadOrders();
  }, [loadOrders]);

  const filteredOrders = orders.filter((o) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return o.order_number.toLowerCase().includes(q);
  });

  const getOrderStatusBadge = (st: string) => {
    switch (st) {
      case "pending":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/10 text-amber-700">
            <Clock className="w-3 h-3 text-amber-600" aria-hidden="true" />
            Pending
          </span>
        );
      case "confirmed":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-700">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" aria-hidden="true" />
            Confirmed
          </span>
        );
      case "completed":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-500/10 text-blue-700">
            <CheckCircle2 className="w-3 h-3 text-blue-600" aria-hidden="true" />
            Completed
          </span>
        );
      case "cancelled":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-destructive/10 text-destructive">
            <XCircle className="w-3 h-3 text-destructive" aria-hidden="true" />
            Cancelled
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-secondary text-foreground capitalize">
            {st}
          </span>
        );
    }
  };

  const getDeliveryStatusBadge = (dst: string) => {
    switch (dst) {
      case "pending":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-secondary text-muted-foreground capitalize">
            Pending Dispatch
          </span>
        );
      case "arranged":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-500/10 text-indigo-700 capitalize">
            Arranged
          </span>
        );
      case "in_transit":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/10 text-amber-700 capitalize">
            In Transit
          </span>
        );
      case "completed":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-700 capitalize">
            Delivered
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-secondary text-foreground capitalize">
            {dst.replace(/_/g, " ")}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Title & Refresh */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-border">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
            Commercial Orders Ledger
          </h1>
          <p className="text-sm text-muted-foreground">
            Audited trade agreements, delivery fulfillment records, and contract amendments
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void loadOrders()}
            disabled={isLoading}
            className="p-2 rounded-lg border border-border bg-card text-foreground hover:bg-secondary transition-colors disabled:opacity-50"
            aria-label="Refresh orders"
          >
            <RotateCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* Filter Tabs & Search */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        {/* Status Filter Buttons */}
        <div className="flex flex-wrap items-center gap-1.5 p-1 bg-secondary rounded-xl text-xs font-semibold">
          {[
            { id: "", label: "All Orders" },
            { id: "pending", label: "Pending" },
            { id: "confirmed", label: "Confirmed" },
            { id: "completed", label: "Completed" },
            { id: "cancelled", label: "Cancelled" },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => {
                setStatusFilter(tab.id);
                setPage(1);
              }}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                statusFilter === tab.id
                  ? "bg-card text-foreground shadow-xs font-bold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-64">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search order number..."
            className="w-full rounded-xl border border-border bg-card pl-9 pr-4 py-1.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary font-medium"
          />
          <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-2" aria-hidden="true" />
        </div>
      </div>

      {/* Main Content Area */}
      {isLoading ? (
        <LoadingState message="Retrieving commercial trade agreements..." />
      ) : error ? (
        <ErrorState
          title="Failed to Load Orders"
          message={error}
          onRetry={() => void loadOrders()}
        />
      ) : filteredOrders.length === 0 ? (
        <EmptyState
          title="No Commercial Orders Found"
          description="You do not have any trade contracts matching the selected filters. Accepted negotiation offers automatically create binding order records."
        />
      ) : (
        <div className="space-y-4">
          {/* Desktop Table View */}
          <div className="hidden md:block rounded-xl border border-border overflow-hidden bg-card shadow-xs">
            <table className="w-full text-left text-xs">
              <thead className="bg-secondary/60 text-muted-foreground border-b border-border font-bold uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="px-5 py-3">Order Number</th>
                  <th className="px-5 py-3">Trading Counterparty</th>
                  <th className="px-5 py-3">Contract Value</th>
                  <th className="px-5 py-3">Order Status</th>
                  <th className="px-5 py-3">Fulfillment</th>
                  <th className="px-5 py-3">Date (UTC)</th>
                  <th className="px-5 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredOrders.map((ord) => {
                  const counterpartyRole =
                    user?.role === "farmer"
                      ? "Commercial Buyer"
                      : "Verified Producer";

                  return (
                    <tr key={ord.id} className="hover:bg-secondary/20 transition-colors">
                      <td className="px-5 py-4 font-mono font-bold text-foreground">
                        {ord.order_number}
                      </td>
                      <td className="px-5 py-4 font-medium text-foreground">
                        <span>{counterpartyRole}</span>
                        <span className="block text-[11px] text-muted-foreground font-mono">
                          {ord.items_count} {ord.items_count === 1 ? "produce item" : "produce items"}
                        </span>
                      </td>
                      <td className="px-5 py-4 font-mono font-bold text-primary">
                        ₹{Number(ord.total_amount).toLocaleString()}
                      </td>
                      <td className="px-5 py-4">{getOrderStatusBadge(ord.status)}</td>
                      <td className="px-5 py-4">{getDeliveryStatusBadge(ord.delivery_status)}</td>
                      <td className="px-5 py-4 text-muted-foreground font-mono text-[11px]">
                        {new Date(ord.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-5 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {ord.status === "completed" && (
                            <button
                              type="button"
                              onClick={() => setSelectedOrderId(ord.id)}
                              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-primary/30 bg-primary/10 text-primary hover:bg-primary/20 text-xs font-semibold transition-colors"
                              title="View & Print Trade Slip"
                              aria-label={`Print Trade Slip for ${ord.order_number}`}
                            >
                              <Printer className="w-3.5 h-3.5" aria-hidden="true" />
                              <span className="hidden lg:inline">Slip</span>
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => setSelectedOrderId(ord.id)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold transition-colors"
                          >
                            <Eye className="w-3.5 h-3.5 text-muted-foreground" aria-hidden="true" />
                            <span>View Order</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Mobile Card View */}
          <div className="grid grid-cols-1 gap-3 md:hidden">
            {filteredOrders.map((ord) => {
              const counterpartyRole =
                user?.role === "farmer"
                  ? "Commercial Buyer"
                  : "Verified Producer";

              return (
                <div
                  key={ord.id}
                  className="p-4 rounded-xl border border-border bg-card space-y-3 shadow-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-sm text-foreground">
                      {ord.order_number}
                    </span>
                    {getOrderStatusBadge(ord.status)}
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-muted-foreground block text-[11px]">Counterparty:</span>
                      <span className="font-semibold text-foreground">{counterpartyRole}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[11px]">Contract Valuation:</span>
                      <span className="font-bold text-primary font-mono">
                        ₹{Number(ord.total_amount).toLocaleString()}
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[11px]">Fulfillment Status:</span>
                      {getDeliveryStatusBadge(ord.delivery_status)}
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[11px]">Produce Items:</span>
                      <span className="text-foreground font-semibold">
                        {ord.items_count} {ord.items_count === 1 ? "item" : "items"}
                      </span>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-border flex items-center justify-end">
                    <button
                      type="button"
                      onClick={() => setSelectedOrderId(ord.id)}
                      className="w-full py-2 rounded-lg bg-secondary text-foreground hover:bg-secondary/80 text-xs font-semibold transition-colors flex items-center justify-center gap-2"
                    >
                      <ShoppingBag className="w-4 h-4 text-primary" aria-hidden="true" />
                      <span>View Order Specifications</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-4 border-t border-border text-xs text-muted-foreground">
              <span>
                Showing {filteredOrders.length} of {totalCount} orders
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

      {/* Order Detail Modal */}
      <OrderDetailModal
        orderId={selectedOrderId}
        onClose={() => setSelectedOrderId(null)}
        onOrderUpdated={() => void loadOrders()}
      />
    </div>
  );
};
