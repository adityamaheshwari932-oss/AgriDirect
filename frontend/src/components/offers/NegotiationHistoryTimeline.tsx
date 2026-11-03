import React from "react";
import { ArrowRight, CheckCircle2, Clock, XCircle, Ban, History } from "lucide-react";
import type { OfferDetail, OfferStatus } from "../../types/offers";

interface NegotiationHistoryTimelineProps {
  history: OfferDetail[];
  currentOfferId: string;
  onSelectOffer?: (offerId: string) => void;
}

export const NegotiationHistoryTimeline: React.FC<NegotiationHistoryTimelineProps> = ({
  history,
  currentOfferId,
  onSelectOffer,
}) => {
  if (!history || history.length === 0) return null;

  const getStatusIcon = (status: OfferStatus) => {
    switch (status) {
      case "accepted":
        return <CheckCircle2 className="w-4 h-4 text-emerald-600" aria-hidden="true" />;
      case "countered":
        return <ArrowRight className="w-4 h-4 text-blue-600" aria-hidden="true" />;
      case "rejected":
        return <XCircle className="w-4 h-4 text-red-600" aria-hidden="true" />;
      case "withdrawn":
        return <Ban className="w-4 h-4 text-amber-600" aria-hidden="true" />;
      case "pending":
      default:
        return <Clock className="w-4 h-4 text-primary" aria-hidden="true" />;
    }
  };

  const getStatusBadge = (status: OfferStatus) => {
    switch (status) {
      case "accepted":
        return "bg-emerald-50 text-emerald-800 border-emerald-200";
      case "countered":
        return "bg-blue-50 text-blue-800 border-blue-200";
      case "rejected":
        return "bg-red-50 text-red-800 border-red-200";
      case "withdrawn":
        return "bg-amber-50 text-amber-800 border-amber-200";
      case "expired":
        return "bg-gray-100 text-gray-800 border-gray-300";
      case "pending":
      default:
        return "bg-primary/10 text-primary border-primary/20";
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-1.5 text-xs font-bold text-foreground uppercase tracking-wider">
        <History className="w-4 h-4 text-primary" aria-hidden="true" />
        <span>Negotiation Lineage ({history.length} round{history.length > 1 ? "s" : ""})</span>
      </div>

      <div className="relative pl-6 space-y-4 before:content-[''] before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-border">
        {history.map((step, idx) => {
          const isSelected = step.id === currentOfferId;
          const senderName = step.sender?.name || step.sender?.business_name || "Participant";
          const senderRole = step.sender?.role || "user";

          return (
            <div
              key={step.id}
              className={`relative p-3 rounded-xl border text-xs transition-all ${
                isSelected
                  ? "bg-primary/5 border-primary shadow-xs ring-1 ring-primary"
                  : "bg-card border-border hover:border-primary/50"
              }`}
            >
              {/* Timeline marker */}
              <div
                className={`absolute -left-[27px] top-3.5 w-4 h-4 rounded-full bg-card border-2 flex items-center justify-center ${
                  isSelected ? "border-primary" : "border-muted-foreground/40"
                }`}
              >
                <div
                  className={`w-1.5 h-1.5 rounded-full ${
                    isSelected ? "bg-primary" : "bg-muted-foreground/40"
                  }`}
                />
              </div>

              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-foreground">
                    Round {idx + 1}: {step.offer_number}
                  </span>
                  {isSelected && (
                    <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-primary text-primary-foreground">
                      Current
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-1.5">
                  <span
                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${getStatusBadge(
                      step.status
                    )}`}
                  >
                    {getStatusIcon(step.status)}
                    <span className="capitalize">{step.status}</span>
                  </span>
                </div>
              </div>

              <div className="text-muted-foreground grid grid-cols-1 sm:grid-cols-2 gap-1 text-[11px]">
                <div>
                  <span className="text-muted-foreground">Proposed by:</span>{" "}
                  <span className="font-semibold text-foreground">
                    {senderName} ({senderRole})
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground">Proposal Total:</span>{" "}
                  <span className="font-bold text-foreground">
                    ₹{Number(step.total_amount).toLocaleString()}
                  </span>
                </div>
              </div>

              {step.items && step.items.length > 0 && (
                <div className="mt-2 pt-2 border-t border-border/60 flex flex-wrap gap-2 text-[11px]">
                  {step.items.map((it) => (
                    <span
                      key={it.id}
                      className="px-2 py-0.5 rounded bg-secondary text-foreground font-medium"
                    >
                      {it.product_name}: {it.quantity} {it.unit} @ ₹{Number(it.unit_price).toLocaleString()}
                    </span>
                  ))}
                </div>
              )}

              {onSelectOffer && !isSelected && (
                <div className="mt-2 pt-1 flex justify-end">
                  <button
                    type="button"
                    onClick={() => onSelectOffer(step.id)}
                    className="text-[11px] text-primary hover:text-primary-800 font-semibold"
                  >
                    View This Version →
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

