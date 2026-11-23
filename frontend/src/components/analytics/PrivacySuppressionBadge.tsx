import React from "react";
import { ShieldCheck, Info } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { PrivacyMeta } from "../../types/analytics";

interface PrivacySuppressionBadgeProps {
  privacy: PrivacyMeta;
}

export const PrivacySuppressionBadge: React.FC<PrivacySuppressionBadgeProps> = ({ privacy }) => {
  const { t } = useTranslation(["analytics"]);

  if (!privacy.is_suppressed) {
    return (
      <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20">
        <ShieldCheck className="w-3.5 h-3.5" />
        {t("analytics:privacy_protected", "Privacy Protected: High Participant Diversity")}
      </div>
    );
  }

  return (
    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-amber-500/10 text-amber-800 dark:text-amber-400 border border-amber-500/20">
      <Info className="w-3.5 h-3.5 shrink-0" />
      <span>
        {privacy.suppression_reason ||
          t("analytics:privacy_suppressed", "Price indices suppressed to protect trader confidentiality")}
      </span>
      {privacy.distinct_farmers_band && (
        <span className="text-[10px] text-muted-foreground ms-1">
          ({t("analytics:farmers_band", "Farmers: {{band}}", { band: privacy.distinct_farmers_band })})
        </span>
      )}
    </div>
  );
};

