import React from "react";
import { Link } from "react-router-dom";
import { ShieldCheck, ArrowLeft, UserCheck } from "lucide-react";
import { useAuth } from "../store/authStore";
import { PageContainer } from "../components/layout/PageContainer";

export const ProtectedPlaceholderPage: React.FC = () => {
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
                Protected Route Verification Placeholder
              </h1>
              <p className="text-xs text-muted-foreground">
                Temporary placeholder to verify authentication route gating
              </p>
            </div>
          </div>

          <div className="p-4 bg-secondary rounded-lg space-y-2 text-sm text-foreground">
            <div className="flex items-center gap-2 text-primary-900 font-semibold mb-2">
              <UserCheck className="w-4 h-4" />
              <span>Authenticated Session Active</span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              This route demonstrates that the <code className="bg-background px-1 py-0.5 rounded text-foreground font-mono">RequireAuth</code> guard
              successfully intercepted the request, resolved session restoration, and verified credentials before rendering.
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
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Overview</span>
            </Link>
          </div>
        </div>
      </PageContainer>
    </div>
  );
};
