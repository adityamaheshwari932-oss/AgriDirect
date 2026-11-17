import React from "react";
import { Link } from "react-router-dom";
import { ShieldCheck, ArrowLeft, UserCheck } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../store/authStore";
import { PageContainer } from "../components/layout/PageContainer";

export const ProtectedPlaceholderPage: React.FC = () => {
  const { t } = useTranslation(["common", "auth"]);
  const { user } = useAuth();

  return (
    <div className="flex-1 py-12">
      <PageContainer size="sm">
        <div className="bg-card p-8 rounded-xl border border-border shadow-sm space-y-6">
          <div className="flex items-center gap-3 pb-4 border-b border-border">
            <div className="w-10 h-10 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center">
              <ShieldCheck className="w-6 h-6" aria-hidden="true" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-foreground">
                {t("auth:protected_placeholder_title", "Protected Route Verification Placeholder")}
              </h1>
              <p className="text-xs text-muted-foreground">
                {t(
                  "auth:protected_placeholder_desc",
                  "Temporary placeholder to verify authentication route gating"
                )}
              </p>
            </div>
          </div>

          <div className="p-4 bg-secondary rounded-lg space-y-2 text-sm text-foreground">
            <div className="flex items-center gap-2 text-primary-900 font-semibold mb-2">
              <UserCheck className="w-4 h-4" />
              <span>{t("auth:session_active", "Authenticated Session Active")}</span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {t(
                "auth:protected_route_notice",
                "This route demonstrates that the RequireAuth guard successfully intercepted the request, resolved session restoration, and verified credentials before rendering."
              )}
            </p>
            {user && (
              <div className="text-xs space-y-1 pt-2 font-mono text-muted-foreground border-t border-border">
                <div>User ID: {user.id}</div>
                <div>Email: {user.email}</div>
                <div>Role: {user.role}</div>
                <div>Verification Status: {user.verification_status}</div>
              </div>
            )}
          </div>

          <div className="pt-2">
            <Link
              to="/"
              className="inline-flex items-center gap-2 text-sm font-medium text-primary hover:text-primary-800"
            >
              <ArrowLeft className="w-4 h-4 rtl:rotate-180" />
              <span>{t("common:actions.back_to_overview", "Back to Overview")}</span>
            </Link>
          </div>
        </div>
      </PageContainer>
    </div>
  );
};
