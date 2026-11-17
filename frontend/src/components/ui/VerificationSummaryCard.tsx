import React from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  ShieldAlert,
  ShieldCheck,
  Clock,
  XCircle,
  ArrowRight,
  FileCheck,
} from "lucide-react";
import type { VerificationStatus } from "../../types";
import { getLocalizedVerificationStatus } from "../../utils/status";

interface VerificationSummaryCardProps {
  status: VerificationStatus;
  role: "farmer" | "buyer" | "admin";
  rejectionReason?: string | null;
  className?: string;
}

export const VerificationSummaryCard: React.FC<VerificationSummaryCardProps> = ({
  status,
  role,
  rejectionReason,
  className = "",
}) => {
  const { t } = useTranslation(["verification", "common"]);
  const config = getLocalizedVerificationStatus(status, t);

  const getStatusIcon = () => {
    switch (status) {
      case "verified":
        return <ShieldCheck className="w-6 h-6 text-emerald-600" aria-hidden="true" />;
      case "pending":
        return <Clock className="w-6 h-6 text-blue-600" aria-hidden="true" />;
      case "rejected":
        return <XCircle className="w-6 h-6 text-red-600" aria-hidden="true" />;
      case "unverified":
      default:
        return <ShieldAlert className="w-6 h-6 text-amber-600" aria-hidden="true" />;
    }
  };

  const getRoleGuidance = () => {
    if (role === "farmer") {
      switch (status) {
        case "verified":
          return "Your farm credentials are verified. You can post produce listings, negotiate bulk volume pricing, and accept commercial contracts.";
        case "pending":
          return "Your identity and farm ownership records are currently under review by AgriDirect administrators. Marketplace posting will unlock once confirmed.";
        case "rejected":
          return "Your documentation did not meet verification criteria. Please inspect reviewer feedback on the verification page and submit clear documents.";
        case "unverified":
        default:
          return "As an agricultural producer, verified identity unlocks bulk produce listings and direct trade communications with restaurants, hotels, and wholesalers.";
      }
    } else {
      switch (status) {
        case "verified":
          return "Your commercial business credentials are verified. You can issue purchase inquiries, post buyer requirements, and finalize direct wholesale agreements.";
        case "pending":
          return "Your business registration and tax identification (GSTIN/CIN) are currently under administrative review. Direct supplier communications will unlock once confirmed.";
        case "rejected":
          return "Your commercial entity verification could not be validated. Please check the rejection notes on the verification page and re-upload valid trade documents.";
        case "unverified":
        default:
          return "Commercial verification is required before initiating supplier negotiations or placing direct wholesale orders. Submit your tax or corporate registration ID to begin.";
      }
    }
  };

  return (
    <div
      className={`p-5 rounded-xl border bg-card shadow-xs space-y-4 ${className}`}
      role="region"
      aria-labelledby="verification-summary-heading"
    >
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-secondary flex items-center justify-center">
            {getStatusIcon()}
          </div>
          <div>
            <h2
              id="verification-summary-heading"
              className="text-base font-bold text-foreground"
            >
              Account Verification Status
            </h2>
            <p className="text-xs text-muted-foreground">
              Independent identity and credential validation
            </p>
          </div>
        </div>

        <span
          className={`inline-flex items-center gap-2 self-start sm:self-auto px-3 py-1 rounded-full text-xs font-semibold border ${config.badgeClass}`}
        >
          <span className={`w-2 h-2 rounded-full ${config.dotClass}`} aria-hidden="true" />
          <span>{config.label}</span>
        </span>
      </div>

      <div className="p-3.5 bg-secondary/50 rounded-lg text-sm text-foreground space-y-1.5 border border-border">
        <p className="font-medium text-xs text-muted-foreground uppercase tracking-wider">
          Marketplace Capability
        </p>
        <p className="text-sm leading-relaxed">{getRoleGuidance()}</p>
      </div>

      {status === "rejected" && rejectionReason && (
        <div className="p-3 bg-red-50 text-red-900 rounded-lg text-xs border border-red-200 space-y-1" role="alert">
          <p className="font-semibold text-red-950">Administrative Rejection Reason:</p>
          <p className="text-red-800 leading-relaxed">{rejectionReason}</p>
        </div>
      )}

      <div className="pt-1 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <FileCheck className="w-4 h-4 text-primary" aria-hidden="true" />
          <span>Verification is managed exclusively by platform administrators</span>
        </div>

        <Link
          to="/dashboard/verification"
          className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold text-primary hover:text-primary-800 hover:bg-primary-50 border border-primary/20 transition-colors focus:outline-none focus:ring-2 focus:ring-primary"
        >
          <span>View Verification Details</span>
          <ArrowRight className="w-3.5 h-3.5 rtl:rotate-180" aria-hidden="true" />
        </Link>
      </div>
    </div>
  );
};
