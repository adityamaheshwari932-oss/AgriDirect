import React, { useState } from "react";
import {
  X,
  AlertCircle,
  Loader2,
  Calendar,
  DollarSign,
  Package,
  FileText,
  CheckCircle2,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { ordersApi } from "../../api/orders";
import type { OrderDetail, AmendmentType } from "../../types/orders";
import { formatNumber } from "../../utils/formatters";

interface AmendmentProposalModalProps {
  isOpen: boolean;
  order: OrderDetail | null;
  onClose: () => void;
  onSuccess: () => void;
}

export const AmendmentProposalModal: React.FC<AmendmentProposalModalProps> = ({
  isOpen,
  order,
  onClose,
  onSuccess,
}) => {
  const { t } = useTranslation(["orders", "validation", "common", "errors"]);
  const [amendmentType, setAmendmentType] = useState<AmendmentType>("quantity");
  const [selectedItemId, setSelectedItemId] = useState<string>(
    order?.items && order.items.length > 0 ? order.items[0].id : ""
  );
  const [newQuantity, setNewQuantity] = useState<number | "">("");
  const [newPrice, setNewPrice] = useState<number | "">("");
  const [newDeliveryDate, setNewDeliveryDate] = useState<string>("");
  const [newTerms, setNewTerms] = useState<string>("");
  const [justification, setJustification] = useState<string>("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const todayStr = new Date().toISOString().split("T")[0];

  if (!isOpen || !order) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const trimmedJustification = justification.trim();
    if (trimmedJustification.length < 3) {
      setError(
        t(
          "orders:amendment.justification_min",
          "Please provide a commercial justification with at least 3 characters."
        )
      );
      return;
    }

    const payload: {
      amendment_type: AmendmentType;
      justification: string;
      order_item_id?: string;
      new_quantity?: number;
      new_price?: number;
      new_delivery_date?: string;
      new_terms?: string;
    } = {
      amendment_type: amendmentType,
      justification: trimmedJustification,
    };

    if (amendmentType === "quantity") {
      if (!selectedItemId) {
        setError(
          t("orders:amendment.select_item_required", "Please select the line item to modify.")
        );
        return;
      }
      const qty = Number(newQuantity);
      if (isNaN(qty) || qty <= 0) {
        setError(
          t(
            "orders:amendment.valid_quantity_required",
            "Please enter a valid new quantity greater than 0."
          )
        );
        return;
      }
      payload.order_item_id = selectedItemId;
      payload.new_quantity = qty;
    } else if (amendmentType === "price") {
      if (!selectedItemId) {
        setError(
          t("orders:amendment.select_item_required", "Please select the line item to modify.")
        );
        return;
      }
      const price = Number(newPrice);
      if (isNaN(price) || price <= 0) {
        setError(
          t(
            "orders:amendment.valid_price_required",
            "Please enter a valid new price greater than 0."
          )
        );
        return;
      }
      payload.order_item_id = selectedItemId;
      payload.new_price = price;
    } else if (amendmentType === "delivery_date") {
      if (!newDeliveryDate) {
        setError(
          t(
            "orders:amendment.date_required",
            "Please select the new proposed delivery date."
          )
        );
        return;
      }
      payload.new_delivery_date = newDeliveryDate;
    } else if (amendmentType === "terms") {
      const terms = newTerms.trim();
      if (terms.length < 3) {
        setError(
          t(
            "orders:amendment.terms_min",
            "Please provide new terms with at least 3 characters."
          )
        );
        return;
      }
      payload.new_terms = terms;
    }

    setIsSubmitting(true);
    try {
      await ordersApi.proposeAmendment(order.id, payload);
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : t("orders:amendment.failed", "Failed to propose amendment.");
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-amendment-propose-title"
    >
      <div className="bg-card w-full max-w-lg rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/40">
          <div>
            <h2 id="modal-amendment-propose-title" className="text-base font-bold text-foreground">
              {t("orders:amendment.title", "Propose Order Amendment")}
            </h2>
            <p className="text-xs text-muted-foreground">
              {t(
                "orders:amendment.subtitle",
                "Amendments require counterparty bilateral approval before taking effect on Order {{orderNumber}}",
                { orderNumber: order.order_number }
              )}
            </p>
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

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3.5 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" aria-hidden="true" />
              <div>
                <p className="font-semibold">{t("orders:amendment.error_title", "Amendment Error")}</p>
                <p>{error}</p>
              </div>
            </div>
          )}

          {/* Type Selector */}
          <div className="space-y-1.5">
            <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground">
              {t("orders:amendment.category_label", "Amendment Category")}
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {(
                [
                  { id: "quantity", label: t("orders:amendment.cat_quantity", "Quantity") },
                  { id: "price", label: t("orders:amendment.cat_price", "Unit Price") },
                  { id: "delivery_date", label: t("orders:amendment.cat_date", "Delivery Date") },
                  { id: "terms", label: t("orders:amendment.cat_terms", "Trade Terms") },
                ] as const
              ).map((tOption) => (
                <button
                  key={tOption.id}
                  type="button"
                  onClick={() => setAmendmentType(tOption.id)}
                  className={`py-2 px-2.5 rounded-xl text-xs font-semibold border transition-all ${
                    amendmentType === tOption.id
                      ? "border-primary bg-primary/10 text-primary font-bold shadow-xs"
                      : "border-border bg-card text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {tOption.label}
                </button>
              ))}
            </div>
          </div>

          {/* Conditional Line Item Selector */}
          {(amendmentType === "quantity" || amendmentType === "price") && (
            <div className="space-y-1.5">
              <label
                htmlFor="amendment-item-select"
                className="block text-xs font-bold uppercase tracking-wider text-muted-foreground"
              >
                {t("orders:amendment.select_item_label", "Select Line Item")}{" "}
                <span className="text-destructive">*</span>
              </label>
              <select
                id="amendment-item-select"
                value={selectedItemId}
                onChange={(e) => setSelectedItemId(e.target.value)}
                className="w-full rounded-xl border border-border bg-card px-3.5 py-2.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary font-medium"
                required
              >
                {order.items.map((it) => (
                  <option key={it.id} value={it.id}>
                    {it.product_name} — Currently {formatNumber(it.quantity)} {it.unit} @ ₹{formatNumber(Number(it.unit_price))}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Dynamic Inputs according to type */}
          {amendmentType === "quantity" && (
            <div className="space-y-1.5">
              <label
                htmlFor="amendment-new-quantity"
                className="block text-xs font-bold uppercase tracking-wider text-muted-foreground"
              >
                {t("orders:amendment.new_quantity_label", "New Proposed Quantity")}{" "}
                <span className="text-destructive">*</span>
              </label>
              <div className="relative">
                <input
                  id="amendment-new-quantity"
                  type="number"
                  step="0.001"
                  min="0.001"
                  value={newQuantity}
                  onChange={(e) =>
                    setNewQuantity(e.target.value === "" ? "" : parseFloat(e.target.value))
                  }
                  placeholder={t(
                    "orders:amendment.new_quantity_placeholder",
                    "Enter amended physical quantity"
                  )}
                  className="w-full rounded-xl border border-border bg-card ps-9 pe-4 py-2.5 text-xs font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  required
                />
                <Package className="w-4 h-4 text-muted-foreground absolute start-3 top-3" aria-hidden="true" />
              </div>
            </div>
          )}

          {amendmentType === "price" && (
            <div className="space-y-1.5">
              <label
                htmlFor="amendment-new-price"
                className="block text-xs font-bold uppercase tracking-wider text-muted-foreground"
              >
                {t("orders:amendment.new_price_label", "New Proposed Unit Price (₹)")}{" "}
                <span className="text-destructive">*</span>
              </label>
              <div className="relative">
                <input
                  id="amendment-new-price"
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={newPrice}
                  onChange={(e) =>
                    setNewPrice(e.target.value === "" ? "" : parseFloat(e.target.value))
                  }
                  placeholder={t(
                    "orders:amendment.new_price_placeholder",
                    "Enter amended unit price"
                  )}
                  className="w-full rounded-xl border border-border bg-card ps-9 pe-4 py-2.5 text-xs font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  required
                />
                <DollarSign className="w-4 h-4 text-muted-foreground absolute start-3 top-3" aria-hidden="true" />
              </div>
            </div>
          )}

          {amendmentType === "delivery_date" && (
            <div className="space-y-1.5">
              <label
                htmlFor="amendment-new-date"
                className="block text-xs font-bold uppercase tracking-wider text-muted-foreground"
              >
                {t("orders:amendment.new_date_label", "New Proposed Delivery Date")}{" "}
                <span className="text-destructive">*</span>
              </label>
              <div className="relative">
                <input
                  id="amendment-new-date"
                  type="date"
                  min={todayStr}
                  value={newDeliveryDate}
                  onChange={(e) => setNewDeliveryDate(e.target.value)}
                  className="w-full rounded-xl border border-border bg-card ps-9 pe-4 py-2.5 text-xs font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  required
                />
                <Calendar className="w-4 h-4 text-muted-foreground absolute start-3 top-3" aria-hidden="true" />
              </div>
            </div>
          )}

          {amendmentType === "terms" && (
            <div className="space-y-1.5">
              <label
                htmlFor="amendment-new-terms"
                className="block text-xs font-bold uppercase tracking-wider text-muted-foreground"
              >
                {t(
                  "orders:amendment.new_terms_label",
                  "New Logistics / Commercial Terms"
                )}{" "}
                <span className="text-destructive">*</span>
              </label>
              <div className="relative">
                <textarea
                  id="amendment-new-terms"
                  rows={3}
                  value={newTerms}
                  onChange={(e) => setNewTerms(e.target.value)}
                  placeholder={t(
                    "orders:amendment.new_terms_placeholder",
                    "Specify amended trade terms..."
                  )}
                  maxLength={2000}
                  className="w-full rounded-xl border border-border bg-card ps-9 pe-4 py-2 text-xs font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  required
                />
                <FileText className="w-4 h-4 text-muted-foreground absolute start-3 top-3" aria-hidden="true" />
              </div>
            </div>
          )}

          {/* Justification */}
          <div className="space-y-1.5">
            <label
              htmlFor="amendment-justification"
              className="block text-xs font-bold uppercase tracking-wider text-muted-foreground"
            >
              {t("orders:amendment.justification_label", "Commercial Justification")}{" "}
              <span className="text-destructive">*</span>
            </label>
            <textarea
              id="amendment-justification"
              rows={2}
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
              placeholder={t(
                "orders:amendment.justification_placeholder",
                "Explain the commercial reason for proposing this post-finalization change..."
              )}
              maxLength={1000}
              className="w-full rounded-xl border border-border bg-card px-3.5 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary font-medium"
              required
            />
          </div>

          <div className="pt-2 flex items-center justify-end gap-3 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-xl border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold transition-colors disabled:opacity-50"
            >
              {t("common:actions.cancel", "Cancel")}
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-bold shadow-xs transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                  <span>{t("orders:amendment.submitting", "Submitting Proposal...")}</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4" aria-hidden="true" />
                  <span>{t("orders:amendment.submit_btn", "Submit Amendment")}</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

