import React from "react";
import { Link } from "react-router-dom";
import { Tractor, Store, ArrowRight, ShieldCheck } from "lucide-react";
import { AuthLayout } from "../components/layout/AuthLayout";

export const RegisterRolePage: React.FC = () => {
  return (
    <AuthLayout
      title="Create your AgriDirect account"
      subtitle="Select your primary operational role to begin direct agricultural trade"
      maxWidth="wide"
    >
      <div className="space-y-6">
        {/* Verification Clarification Notice */}
        <div className="p-3.5 bg-secondary/80 border border-border rounded-lg flex items-start gap-3 text-muted-foreground text-xs leading-relaxed">
          <ShieldCheck className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" aria-hidden="true" />
          <span>
            Registration establishes your platform account and initial profile.
            Formal document verification is completed separately before produce listings or purchase orders can be created.
          </span>
        </div>

        {/* Role Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Farmer Card */}
          <div className="border border-border rounded-xl p-6 bg-card hover:border-primary transition-all flex flex-col justify-between shadow-xs">
            <div>
              <div className="w-12 h-12 rounded-lg bg-primary-50 text-primary-700 flex items-center justify-center mb-4">
                <Tractor className="w-6 h-6" aria-hidden="true" />
              </div>
              <h2 className="text-lg font-bold text-foreground mb-2">Agricultural Producer</h2>
              <p className="text-xs text-muted-foreground leading-relaxed mb-4">
                For individual farmers, family farms, agricultural cooperatives, and producers seeking
                direct commercial sales without commission-heavy intermediaries.
              </p>
            </div>
            <Link
              to="/register/farmer"
              className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-primary text-primary-foreground font-semibold text-sm hover:bg-primary-700 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
            >
              <span>Register as a Farmer</span>
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </Link>
          </div>

          {/* Buyer Card */}
          <div className="border border-border rounded-xl p-6 bg-card hover:border-harvest-500 transition-all flex flex-col justify-between shadow-xs">
            <div>
              <div className="w-12 h-12 rounded-lg bg-harvest-50 text-harvest-700 flex items-center justify-center mb-4">
                <Store className="w-6 h-6" aria-hidden="true" />
              </div>
              <h2 className="text-lg font-bold text-foreground mb-2">Commercial Buyer</h2>
              <p className="text-xs text-muted-foreground leading-relaxed mb-4">
                For restaurants, hotels, supermarket chains, wholesalers, food processors, and caterers
                procuring fresh bulk produce directly with clear provenance.
              </p>
            </div>
            <Link
              to="/register/buyer"
              className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-harvest-600 text-white font-semibold text-sm hover:bg-harvest-700 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-harvest-600 focus:ring-offset-2"
            >
              <span>Register as a Buyer</span>
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </Link>
          </div>
        </div>

        {/* Existing Account Footer Link */}
        <div className="pt-4 border-t border-border text-center text-xs text-muted-foreground">
          Already registered?{" "}
          <Link
            to="/login"
            className="font-semibold text-primary hover:text-primary-800 underline focus:outline-none focus:ring-2 focus:ring-primary rounded"
          >
            Sign in to existing account
          </Link>
        </div>
      </div>
    </AuthLayout>
  );
};
