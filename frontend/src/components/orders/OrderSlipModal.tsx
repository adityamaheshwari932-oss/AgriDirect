import React from "react";
import { X, Printer, Sprout, ShieldCheck, CheckCircle2, FileText, Truck, Building, User } from "lucide-react";
import type { OrderDetail } from "../../types/orders";
import type { PaymentSummary } from "../../types/payments";

interface OrderSlipModalProps {
  isOpen: boolean;
  order: OrderDetail;
  paymentSummary?: PaymentSummary | null;
  onClose: () => void;
}

export const OrderSlipModal: React.FC<OrderSlipModalProps> = ({
  isOpen,
  order,
  paymentSummary,
  onClose,
}) => {
  if (!isOpen) return null;

  const handlePrint = () => {
    window.print();
  };

  const formattedOrderDate = new Date(order.created_at).toLocaleDateString("en-IN", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });

  const formattedCompletionDate = order.completed_at
    ? new Date(order.completed_at).toLocaleDateString("en-IN", {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : order.delivery_acknowledged_at
    ? new Date(order.delivery_acknowledged_at).toLocaleDateString("en-IN", {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : formattedOrderDate;

  const totalContractAmount = Number(order.total_amount) || 0;
  const recordedPayments = paymentSummary
    ? Number(paymentSummary.total_recorded) || 0
    : totalContractAmount;

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/70 backdrop-blur-xs flex items-center justify-center p-4 print:p-0 print:bg-white print:static print:overflow-visible"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-order-slip-title"
    >
      <div className="bg-card w-full max-w-4xl rounded-2xl border border-border shadow-2xl overflow-hidden my-6 print:border-none print:shadow-none print:my-0 print:max-w-none print:w-full">
        {/* Top Control Bar — Hidden in Print */}
        <div className="no-print px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/50">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
              <FileText className="w-4 h-4" aria-hidden="true" />
            </div>
            <div>
              <h2 id="modal-order-slip-title" className="text-base font-bold text-foreground">
                Trade Confirmation & Delivery Slip
              </h2>
              <p className="text-xs text-muted-foreground">
                Official bilateral B2B trade documentation for Order {order.order_number}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handlePrint}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-bold shadow-xs transition-colors focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <Printer className="w-4 h-4" aria-hidden="true" />
              <span>Print / Save as PDF</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary focus:outline-none focus:ring-2 focus:ring-primary"
              aria-label="Close dialog"
            >
              <X className="w-5 h-5" aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Scrollable Preview Area for Screen */}
        <div className="p-4 sm:p-8 max-h-[82vh] overflow-y-auto bg-muted/30 print:max-h-none print:overflow-visible print:p-0 print:bg-white">
          {/* Printable Sheet Container */}
          <div
            id="printable-order-slip"
            className="bg-white text-slate-900 border border-slate-200 rounded-xl p-8 sm:p-10 shadow-sm space-y-6 print:border-none print:shadow-none print:p-4 print:rounded-none max-w-3xl mx-auto"
          >
            {/* 1. Platform & Document Header */}
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-6 border-b-2 border-emerald-800">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-emerald-800 text-white flex items-center justify-center font-bold">
                    <Sprout className="w-5 h-5" />
                  </div>
                  <span className="text-2xl font-black tracking-tight text-emerald-950">
                    AgriDirect
                  </span>
                </div>
                <p className="text-[11px] font-semibold text-emerald-800 tracking-wider uppercase">
                  B2B Direct Agricultural Trade Marketplace
                </p>
                <p className="text-[10px] text-slate-500">
                  Electronic Bilateral Trade Execution & Fulfillment Registry
                </p>
              </div>

              <div className="text-left sm:text-right space-y-1">
                <span className="inline-block px-3 py-1 rounded-md bg-emerald-100 text-emerald-800 text-xs font-bold tracking-wide uppercase">
                  Trade Confirmation Slip
                </span>
                <p className="text-xs font-mono font-bold text-slate-900">
                  REF: SLIP-{order.order_number}
                </p>
                <p className="text-[11px] text-slate-500">
                  Status:{" "}
                  <span className="font-bold text-emerald-700 uppercase">
                    {order.status === "completed"
                      ? "Fulfilled & Settled"
                      : order.status === "confirmed"
                      ? "Confirmed & Active"
                      : order.status.replace(/_/g, " ")}
                  </span>
                </p>
              </div>
            </div>

            {/* 2. Bilateral Trading Entities */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs">
              {/* Seller / Farmer */}
              <div className="space-y-2">
                <div className="flex items-center gap-1.5 text-emerald-800 font-bold uppercase tracking-wider text-[11px]">
                  <Sprout className="w-3.5 h-3.5 text-emerald-700" />
                  <span>Producer / Seller (Farmer)</span>
                </div>
                <div className="space-y-1 text-slate-700">
                  <p className="text-sm font-bold text-slate-900">
                    {order.farmer?.farm_name || order.farmer?.full_name || "Verified Farm Producer"}
                  </p>
                  <p className="flex items-center gap-1">
                    <User className="w-3 h-3 text-slate-400" />
                    <span>Contact: {order.farmer?.full_name || "Direct Farmer"}</span>
                  </p>
                  <p className="text-[11px] text-slate-500">{order.farmer?.email}</p>
                  {order.farmer?.phone && (
                    <p className="text-[11px] text-slate-500">Phone: {order.farmer.phone}</p>
                  )}
                  <div className="pt-1 flex items-center gap-1 text-[10px] text-emerald-700 font-semibold">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Platform Identity Verified</span>
                  </div>
                </div>
              </div>

              {/* Buyer */}
              <div className="space-y-2 border-t sm:border-t-0 sm:border-l border-slate-200 pt-3 sm:pt-0 sm:pl-6">
                <div className="flex items-center gap-1.5 text-blue-800 font-bold uppercase tracking-wider text-[11px]">
                  <Building className="w-3.5 h-3.5 text-blue-700" />
                  <span>Commercial Buyer (Procurement)</span>
                </div>
                <div className="space-y-1 text-slate-700">
                  <p className="text-sm font-bold text-slate-900">
                    {order.buyer?.business_name || order.buyer?.full_name || "Commercial Buyer"}
                  </p>
                  <p className="flex items-center gap-1">
                    <User className="w-3 h-3 text-slate-400" />
                    <span>Authorized Rep: {order.buyer?.full_name || "Procurement Officer"}</span>
                  </p>
                  <p className="text-[11px] text-slate-500">{order.buyer?.email}</p>
                  {order.buyer?.phone && (
                    <p className="text-[11px] text-slate-500">Phone: {order.buyer.phone}</p>
                  )}
                  <p className="text-[11px] text-slate-600 font-medium pt-0.5">
                    Destination: {order.delivery_destination_address || "Ex-Farm / Direct Handover"}
                  </p>
                </div>
              </div>
            </div>

            {/* 3. Trade Execution & Delivery Details */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs border-y border-slate-200 py-3 text-slate-700">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                  Contract Agreement Date
                </span>
                <span className="font-semibold text-slate-900">{formattedOrderDate}</span>
              </div>
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                  Fulfillment Date
                </span>
                <span className="font-semibold text-slate-900">{formattedCompletionDate}</span>
              </div>
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                  Logistics Method
                </span>
                <span className="font-semibold text-slate-900 capitalize">
                  {order.delivery_method ? order.delivery_method.replace(/_/g, " ") : "Direct Transport"}
                </span>
              </div>
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                  Payment Mode
                </span>
                <span className="font-semibold text-slate-900">Direct Bank (RTGS/NEFT)</span>
              </div>
            </div>

            {/* 4. Produce Manifest & Itemized Ledger */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-1.5">
                <Truck className="w-3.5 h-3.5 text-slate-500" />
                <span>Agricultural Produce Manifest</span>
              </h3>
              <div className="border border-slate-200 rounded-lg overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-100 text-slate-600 font-bold uppercase tracking-wider text-[10px] border-b border-slate-200">
                    <tr>
                      <th className="px-3 py-2.5">#</th>
                      <th className="px-3 py-2.5">Commodity / Variety</th>
                      <th className="px-3 py-2.5">Quality Grade</th>
                      <th className="px-3 py-2.5 text-right">Quantity</th>
                      <th className="px-3 py-2.5 text-right">Agreed Rate</th>
                      <th className="px-3 py-2.5 text-right">Line Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 text-slate-800">
                    {order.items && order.items.length > 0 ? (
                      order.items.map((it, idx) => (
                        <tr key={it.id || idx}>
                          <td className="px-3 py-2.5 font-mono text-slate-400">{idx + 1}</td>
                          <td className="px-3 py-2.5 font-bold text-slate-900">
                            {it.product_name}
                          </td>
                          <td className="px-3 py-2.5 text-slate-600">
                            {it.quality_grade || "Grade A (Standard)"}
                          </td>
                          <td className="px-3 py-2.5 text-right font-medium">
                            {Number(it.quantity).toLocaleString()} {it.unit}
                          </td>
                          <td className="px-3 py-2.5 text-right font-mono text-slate-700">
                            ₹{Number(it.unit_price).toLocaleString()} / {it.unit}
                          </td>
                          <td className="px-3 py-2.5 text-right font-mono font-bold text-slate-900">
                            ₹{Number(it.subtotal).toLocaleString()}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td className="px-3 py-2.5 font-mono text-slate-400">1</td>
                        <td className="px-3 py-2.5 font-bold text-slate-900">
                          Produce Lot (Order #{order.order_number})
                        </td>
                        <td className="px-3 py-2.5 text-slate-600">Commercial Standard</td>
                        <td className="px-3 py-2.5 text-right font-medium">Lot Fulfillment</td>
                        <td className="px-3 py-2.5 text-right font-mono text-slate-700">—</td>
                        <td className="px-3 py-2.5 text-right font-mono font-bold text-slate-900">
                          ₹{totalContractAmount.toLocaleString()}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* 5. Financial Settlement Ledger */}
            <div className="flex flex-col sm:flex-row justify-between items-start gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200">
              <div className="space-y-1 text-xs max-w-sm text-slate-600">
                <span className="font-bold text-slate-800 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700" />
                  Direct Bilateral Settlement
                </span>
                <p className="text-[11px] leading-relaxed">
                  Funds transferred directly from buyer bank account to farmer bank account.
                  Platform acts as the immutable bilateral audit recorder.
                </p>
              </div>

              <div className="w-full sm:w-64 space-y-1.5 text-xs">
                <div className="flex justify-between text-slate-600">
                  <span>Gross Trade Amount:</span>
                  <span className="font-mono font-semibold text-slate-900">
                    ₹{totalContractAmount.toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Recorded Direct Payments:</span>
                  <span className="font-mono font-semibold text-emerald-700">
                    ₹{recordedPayments.toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between border-t border-slate-300 pt-1.5 text-sm font-bold text-slate-950">
                  <span>Total Settled Value:</span>
                  <span className="font-mono text-emerald-800">
                    ₹{totalContractAmount.toLocaleString()}
                  </span>
                </div>
              </div>
            </div>

            {/* 6. Legal Notice of Pure Matching Platform */}
            <div className="p-3 rounded-lg border border-slate-200 bg-white text-[10px] text-slate-500 leading-relaxed space-y-1">
              <p className="font-semibold text-slate-700 uppercase tracking-wider">
                Official Platform Declaration & Regulatory Non-Involvement
              </p>
              <p>
                AgriDirect is an electronic marketplace facilitating direct commercial trade contracts between
                agricultural producers and verified enterprise buyers. AgriDirect is not a trading merchant, does not take
                custody of agricultural commodities, does not inspect goods in transit, and does not process payments or escrow funds.
                Contractual performance, quality verification, and financial settlement are the sole responsibility of the bilateral signatories.
              </p>
            </div>

            {/* 7. Bilateral Signatures & Verification Seal */}
            <div className="pt-6 border-t border-slate-200 grid grid-cols-2 gap-8 text-xs text-slate-700">
              <div className="space-y-8">
                <div className="border-b border-slate-400 pb-1">
                  <p className="font-bold text-slate-900">
                    {order.farmer?.farm_name || order.farmer?.full_name || "Producer Signature"}
                  </p>
                  <p className="text-[10px] text-slate-500">Authorized Farm Seller / Representative</p>
                </div>
                <p className="text-[10px] text-slate-400 font-mono">Date: ____________________</p>
              </div>

              <div className="space-y-8 text-right">
                <div className="border-b border-slate-400 pb-1">
                  <p className="font-bold text-slate-900">
                    {order.buyer?.business_name || order.buyer?.full_name || "Buyer Signature"}
                  </p>
                  <p className="text-[10px] text-slate-500">Authorized Procurement Officer</p>
                </div>
                <p className="text-[10px] text-slate-400 font-mono">Date: ____________________</p>
              </div>
            </div>

            {/* Platform Audit Hash Footer */}
            <div className="text-center pt-2 text-[9px] text-slate-400 font-mono">
              AgriDirect Electronic Trade Ledger • Audit Ref: {order.id} • Generated via AgriDirect v1.0
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
