import React from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Tractor, Store, Truck, ArrowRight, ShieldCheck } from "lucide-react";
import { AuthLayout } from "../components/layout/AuthLayout";

export const RegisterRolePage: React.FC = () => {
  const { t } = useTranslation("auth");

  return (
    <AuthLayout
      title={t("register.title", "Create your AgriDirect account")}
      subtitle={t(
        "register.subtitle",
        "Select your primary operational role to begin direct agricultural trade"
      )}
      maxWidth="wide"
    >
      <div className="space-y-6">
        {/* Verification Clarification Notice */}
        <div className="p-3.5 bg-secondary/80 border border-border rounded-lg flex items-start gap-3 text-muted-foreground text-xs leading-relaxed">
          <ShieldCheck className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" aria-hidden="true" />
          <span>
            {t(
              "register.verification_notice",
              "Registration establishes your platform account and initial profile. Formal document verification is completed separately before produce listings or purchase orders can be created."
            )}
          </span>
        </div>

        {/* Role Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Farmer Card */}
          <div className="border border-border rounded-xl p-6 bg-card hover:border-primary transition-all flex flex-col justify-between shadow-xs">
            <div>
              <div className="w-12 h-12 rounded-lg bg-primary-50 text-primary-700 flex items-center justify-center mb-4">
                <Tractor className="w-6 h-6" aria-hidden="true" />
              </div>
              <h2 className="text-lg font-bold text-foreground mb-2">
                {t("register.farmer_title", "Agricultural Producer")}
              </h2>
              <p className="text-xs text-muted-foreground leading-relaxed mb-4">
                {t(
                  "register.farmer_desc",
                  "For individual farmers, family farms, agricultural cooperatives, and producers seeking direct commercial sales without commission-heavy intermediaries."
                )}
              </p>
            </div>
            <Link
              to="/register/farmer"
              className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-primary text-primary-foreground font-semibold text-sm hover:bg-primary-700 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
            >
              <span>{t("register.farmer_button", "Register as a Farmer")}</span>
              <ArrowRight className="w-4 h-4 rtl:rotate-180" aria-hidden="true" />
            </Link>
          </div>

          {/* Buyer Card */}
          <div className="border border-border rounded-xl p-6 bg-card hover:border-harvest-500 transition-all flex flex-col justify-between shadow-xs">
            <div>
              <div className="w-12 h-12 rounded-lg bg-harvest-50 text-harvest-700 flex items-center justify-center mb-4">
                <Store className="w-6 h-6" aria-hidden="true" />
              </div>
              <h2 className="text-lg font-bold text-foreground mb-2">
                {t("register.buyer_title", "Commercial Buyer")}
              </h2>
              <p className="text-xs text-muted-foreground leading-relaxed mb-4">
                {t(
                  "register.buyer_desc",
                  "For restaurants, hotels, supermarket chains, wholesalers, food processors, and caterers procuring fresh bulk produce directly with clear provenance."
                )}
              </p>
            </div>
            <Link
              to="/register/buyer"
              className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-harvest-600 text-white font-semibold text-sm hover:bg-harvest-700 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-harvest-600 focus:ring-offset-2"
            >
              <span>{t("register.buyer_button", "Register as a Buyer")}</span>
              <ArrowRight className="w-4 h-4 rtl:rotate-180" aria-hidden="true" />
            </Link>
          </div>

          {/* Transporter Card */}
          <div className="border border-border rounded-xl p-6 bg-card hover:border-blue-500 transition-all flex flex-col justify-between shadow-xs">
            <div>
              <div className="w-12 h-12 rounded-lg bg-blue-50 text-blue-700 flex items-center justify-center mb-4">
                <Truck className="w-6 h-6" aria-hidden="true" />
              </div>
              <h2 className="text-lg font-bold text-foreground mb-2">
                {t("register.transporter_title", "Transportation Provider")}
              </h2>
              <p className="text-xs text-muted-foreground leading-relaxed mb-4">
                {t(
                  "register.transporter_desc",
                  "For logistics operators, independent truck owners, fleet managers, and regional haulers providing farm-to-buyer agricultural transport."
                )}
              </p>
            </div>
            <Link
              to="/register/transporter"
              className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-blue-600 text-white font-semibold text-sm hover:bg-blue-700 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
            >
              <span>{t("register.transporter_button", "Register as Transporter")}</span>
              <ArrowRight className="w-4 h-4 rtl:rotate-180" aria-hidden="true" />
            </Link>
          </div>
        </div>

        {/* Existing Account Footer Link */}
        <div className="pt-4 border-t border-border text-center text-xs text-muted-foreground">
          {t("register.already_registered", "Already registered?")}{" "}
          <Link
            to="/login"
            className="font-semibold text-primary hover:text-primary-800 underline focus:outline-none focus:ring-2 focus:ring-primary rounded"
          >
            {t("register.sign_in_link", "Sign in to existing account")}
          </Link>
        </div>
      </div>
    </AuthLayout>
  );
};
