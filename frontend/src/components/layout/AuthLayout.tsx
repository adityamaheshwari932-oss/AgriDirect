import React from "react";
import { Link } from "react-router-dom";
import { Sprout } from "lucide-react";
import { PageContainer } from "./PageContainer";
import { cn } from "../../utils/cn";

interface AuthLayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle?: string;
  maxWidth?: "default" | "wide";
}

export const AuthLayout: React.FC<AuthLayoutProps> = ({
  children,
  title,
  subtitle,
  maxWidth = "default",
}) => {
  return (
    <div className="flex-1 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 bg-background">
      <PageContainer size="sm" className={cn(maxWidth === "wide" && "max-w-2xl")}>
        <div className="text-center mb-8">
          <Link
            to="/"
            className="inline-flex items-center gap-2 mb-4 focus:outline-none focus:ring-2 focus:ring-primary rounded-lg p-1"
            aria-label="Back to AgriDirect Home"
          >
            <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center text-primary-foreground shadow-sm">
              <Sprout className="w-6 h-6" aria-hidden="true" />
            </div>
            <span className="text-2xl font-bold tracking-tight text-primary-900">
              AgriDirect
            </span>
          </Link>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
            {title}
          </h1>
          {subtitle && (
            <p className="mt-2 text-sm text-muted-foreground max-w-md mx-auto">
              {subtitle}
            </p>
          )}
        </div>

        <div className="bg-card py-8 px-6 sm:px-10 shadow-sm rounded-xl border border-border">
          {children}
        </div>
      </PageContainer>
    </div>
  );
};
