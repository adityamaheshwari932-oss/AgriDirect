import React from "react";
import { CheckCircle2, Clock, AlertTriangle, ShieldAlert } from "lucide-react";
import type { PaymentSummary } from "../../types/payments";

interface PaymentSummaryCardProps {
  summary: PaymentSummary | null;
  isLoading?: boolean;
}

export const PaymentSummaryCard: React.FC<PaymentSummaryCardProps> = ({
  summary,
  isLoading = false,
}) => {
  if (isLoading) {
    return (
      <div className="p-4 rounded-xl border border-border bg-card animate-pulse space-y-3">
        <div className="h-4 bg-secondary rounded w-1/3" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <div className="h-12 bg-secondary rounded" />
          <div className="h-12 bg-secondary rounded" />
          <div className="h-12 bg-secondary rounded" />
          <div className="h-12 bg-secondary rounded" />
        </div>
      </div>
    );
  }

  if (!summary) return null;

  const getStatusBadge = (st: string) => {
    switch (st) {
      case "fully_settled":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-700">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" aria-hidden="true" />
            Fully Settled
          </span>
        );
      case "partially_settled":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-500/10 text-blue-700">
            <Clock className="w-3 h-3 text-blue-600" aria-hidden="true" />
            Partially Settled
          </span>
        );
      case "payment_pending_acknowledgement":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/10 text-amber-700">
            <Clock className="w-3 h-3 text-amber-600" aria-hidden="true" />
            Pending Farmer Ack
          </span>
        );
      case "disputed":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-destructive/10 text-destructive">
            <AlertTriangle className="w-3 h-3 text-destructive" aria-hidden="true" />
            Disputed Claim
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-secondary text-muted-foreground capitalize">
            Unpaid
          </span>
        );
    }
  };

  return (
    <div className="rounded-xl border border-border bg-card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
          Off-Platform Payment Reconciliation
        </span>
        {getStatusBadge(summary.settlement_status)}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div className="p-2.5 rounded-lg bg-secondary/40 border border-border/50">
          <span className="text-muted-foreground block text-[11px]">Agreed Order Total</span>
          <span className="font-bold text-foreground text-sm">₹{Number(summary.order_total).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
        </div>

        <div className="p-2.5 rounded-lg bg-emerald-500/5 border border-emerald-500/20">
          <span className="text-emerald-700 block text-[11px] font-semibold">Confirmed Received</span>
          <span className="font-bold text-emerald-800 text-sm">₹{Number(summary.total_acknowledged).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
        </div>

        <div className="p-2.5 rounded-lg bg-amber-500/5 border border-amber-500/20">
          <span className="text-amber-700 block text-[11px] font-semibold">Pending Farmer Ack</span>
          <span className="font-bold text-amber-800 text-sm">₹{Number(summary.unacknowledged_amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
        </div>

        <div className="p-2.5 rounded-lg bg-secondary/40 border border-border/50">
          <span className="text-muted-foreground block text-[11px]">Unsettled Balance</span>
          <span className="font-bold text-foreground text-sm">₹{Number(summary.remaining_acknowledged_balance).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
        </div>
      </div>

      {Number(summary.total_disputed) > 0 && (
        <div className="p-2.5 rounded-lg bg-destructive/10 border border-destructive/20 text-xs text-destructive flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <ShieldAlert className="w-4 h-4 shrink-0" aria-hidden="true" />
            <span>Active Contested Dispute Balance</span>
          </div>
          <span className="font-bold">₹{Number(summary.total_disputed).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
        </div>
      )}
    </div>
  );
};

