import React, { useEffect, useState } from "react";
import {
  X,
  ClipboardList,
  Loader2,
  AlertCircle,
  ArrowUpRight,
  ArrowDownLeft,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { ordersApi } from "../../api/orders";
import type { InventoryAdjustment } from "../../types/orders";
import { formatDate, formatNumber } from "../../utils/formatters";

interface InventoryAuditModalProps {
  isOpen: boolean;
  orderId: string | null;
  orderNumber: string;
  onClose: () => void;
}

export const InventoryAuditModal: React.FC<InventoryAuditModalProps> = ({
  isOpen,
  orderId,
  orderNumber,
  onClose,
}) => {
  const { t } = useTranslation(["orders", "common", "errors"]);
  const [adjustments, setAdjustments] = useState<InventoryAdjustment[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !orderId) {
      setAdjustments([]);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);
    ordersApi
      .getOrderInventoryAdjustments(orderId)
      .then((res) => {
        setAdjustments(res.items || []);
      })
      .catch((err) => {
        const msg =
          err instanceof Error
            ? err.message
            : t(
                "orders:audit.failed",
                "Failed to retrieve immutable inventory adjustment records."
              );
        setError(msg);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [isOpen, orderId, t]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-inventory-audit-title"
    >
      <div className="bg-card w-full max-w-2xl rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/40">
          <div className="flex items-center gap-2">
            <ClipboardList className="w-5 h-5 text-primary" aria-hidden="true" />
            <div>
              <h2 id="modal-inventory-audit-title" className="text-base font-bold text-foreground">
                {t("orders:audit.title", "Immutable Inventory Audit Ledger")}
              </h2>
              <p className="text-xs text-muted-foreground">
                {t(
                  "orders:audit.subtitle",
                  "Order Reference: {{orderNumber}} — Append-only stock movements",
                  { orderNumber }
                )}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary focus:outline-none focus:ring-2 focus:ring-primary"
            aria-label={t("common:actions.close", "Close dialog")}
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 max-h-[70vh] overflow-y-auto space-y-4">
          {isLoading ? (
            <div className="py-12 flex flex-col items-center justify-center text-muted-foreground gap-3">
              <Loader2 className="w-8 h-8 animate-spin text-primary" aria-hidden="true" />
              <p className="text-sm">{t("orders:audit.loading", "Auditing inventory ledgers...")}</p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" aria-hidden="true" />
              <div>
                <p className="font-semibold">{t("orders:audit.error_title", "Audit Retrieval Error")}</p>
                <p>{error}</p>
              </div>
            </div>
          ) : adjustments.length === 0 ? (
            <div className="py-10 text-center text-xs text-muted-foreground">
              {t("orders:audit.empty", "No inventory adjustments recorded for this order yet.")}
            </div>
          ) : (
            <div className="rounded-xl border border-border overflow-hidden">
              <table className="w-full text-left text-xs">
                <thead className="bg-secondary/60 text-muted-foreground border-b border-border font-bold">
                  <tr>
                    <th className="px-4 py-2.5">{t("orders:audit.col_recorded_at", "Recorded At (UTC)")}</th>
                    <th className="px-4 py-2.5">{t("orders:audit.col_change_type", "Change Type")}</th>
                    <th className="px-4 py-2.5 text-right">{t("orders:audit.col_delta", "Delta")}</th>
                    <th className="px-4 py-2.5">{t("orders:audit.col_notes", "Audit Notes")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {adjustments.map((adj) => {
                    const numDelta = Number(adj.quantity_delta);
                    const isPositive = numDelta > 0;
                    return (
                      <tr key={adj.id} className="hover:bg-secondary/20 transition-colors">
                        <td className="px-4 py-3 text-muted-foreground font-mono text-[11px] whitespace-nowrap">
                          {formatDate(adj.created_at, { hour: "2-digit", minute: "2-digit" })}
                        </td>
                        <td className="px-4 py-3">
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-secondary text-foreground capitalize">
                            {adj.change_type.replace(/_/g, " ")}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right font-mono font-bold whitespace-nowrap">
                          <span
                            className={`inline-flex items-center gap-0.5 ${
                              isPositive ? "text-emerald-700" : "text-amber-700"
                            }`}
                          >
                            {isPositive ? (
                              <ArrowUpRight className="w-3.5 h-3.5 rtl:-scale-x-100" aria-hidden="true" />
                            ) : (
                              <ArrowDownLeft className="w-3.5 h-3.5 rtl:-scale-x-100" aria-hidden="true" />
                            )}
                            {isPositive ? `+${formatNumber(numDelta)}` : formatNumber(numDelta)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-muted-foreground text-[11px]">
                          {adj.notes || t("orders:audit.system_adjustment", "System balance adjustment")}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-border flex items-center justify-between bg-secondary/20">
          <span className="text-[11px] text-muted-foreground">
            {t("orders:audit.footer_note", "Strict append-only stock audit ledger per ADR-002")}
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold transition-colors"
          >
            {t("common:actions.close", "Close")}
          </button>
        </div>
      </div>
    </div>
  );
};

