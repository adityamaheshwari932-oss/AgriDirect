import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Sprout, Menu, X, LogOut, User as UserIcon } from "lucide-react";
import { useAuth } from "../../store/authStore";
import { PageContainer } from "./PageContainer";

export const PublicHeader: React.FC = () => {
  const { status, user, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    setMobileMenuOpen(false);
    navigate("/");
  };

  const isAuthenticated = status === "authenticated" && user !== null;

  return (
    <header className="border-b border-border bg-card/95 backdrop-blur sticky top-0 z-40 transition-colors">
      {/* Top Announcement Bar */}
      <div className="bg-primary-900 text-white text-xs py-1.5 px-4 text-center tracking-wide font-medium flex items-center justify-center gap-2">
        <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse" aria-hidden="true" />
        <span>AgriDirect — Direct B2B Agricultural Trade Platform</span>
      </div>

      <PageContainer>
        <div className="h-16 flex items-center justify-between">
          {/* Brand Logo */}
          <Link
            to="/"
            className="flex items-center gap-3 focus:outline-none focus:ring-2 focus:ring-primary rounded-lg p-1"
            aria-label="AgriDirect Home"
          >
            <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center text-primary-foreground shadow-sm">
              <Sprout className="w-6 h-6" aria-hidden="true" />
            </div>
            <div>
              <span className="text-xl font-bold tracking-tight text-primary-900 block leading-tight">
                AgriDirect
              </span>
              <span className="text-[10px] text-muted-foreground uppercase tracking-widest font-semibold block">
                Agricultural Marketplace
              </span>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-6" aria-label="Main Navigation">
            <Link
              to="/"
              className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              Overview
            </Link>

            {isAuthenticated ? (
              <div className="flex items-center gap-3 pl-4 border-l border-border">
                <Link
                  to="/dashboard"
                  className="text-xs font-semibold text-primary hover:text-primary-800 transition-colors bg-primary/10 hover:bg-primary/20 px-3 py-1.5 rounded-md"
                >
                  Dashboard
                </Link>
                <div className="flex items-center gap-2 text-xs text-foreground bg-secondary px-3 py-1.5 rounded-full">
                  <UserIcon className="w-3.5 h-3.5 text-muted-foreground" aria-hidden="true" />
                  <span className="font-semibold capitalize text-primary-900">
                    {user.role}
                  </span>
                  <span className="text-muted-foreground">•</span>
                  <span className="text-muted-foreground truncate max-w-[150px]">
                    {user.email}
                  </span>
                </div>

                <button
                  type="button"
                  onClick={handleLogout}
                  className="inline-flex items-center gap-1.5 text-xs font-medium text-destructive hover:text-destructive/80 transition-colors px-2 py-1 rounded focus:outline-none focus:ring-2 focus:ring-destructive"
                >
                  <LogOut className="w-3.5 h-3.5" aria-hidden="true" />
                  Sign Out
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-3 pl-4 border-l border-border">
                <Link
                  to="/login"
                  className="text-sm font-medium text-foreground hover:text-primary transition-colors px-3 py-2 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  className="inline-flex items-center justify-center text-sm font-medium bg-primary text-primary-foreground hover:bg-primary-700 transition-colors px-4 py-2 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
                >
                  Register
                </Link>
              </div>
            )}
          </nav>

          {/* Mobile Menu Button */}
          <div className="flex md:hidden">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary focus:outline-none focus:ring-2 focus:ring-primary"
              aria-expanded={mobileMenuOpen}
              aria-label={mobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
            >
              {mobileMenuOpen ? (
                <X className="w-6 h-6" aria-hidden="true" />
              ) : (
                <Menu className="w-6 h-6" aria-hidden="true" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile Navigation Dropdown */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-border py-4 space-y-3">
            <Link
              to="/"
              onClick={() => setMobileMenuOpen(false)}
              className="block text-sm font-medium text-foreground px-3 py-2 rounded-md hover:bg-secondary"
            >
              Overview
            </Link>

            {isAuthenticated ? (
              <div className="pt-2 border-t border-border space-y-3 px-3">
                <Link
                  to="/dashboard"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block text-sm font-semibold text-primary hover:text-primary-800"
                >
                  Go to Dashboard
                </Link>
                <div className="text-xs text-muted-foreground">
                  Signed in as <strong className="text-foreground">{user.email}</strong> ({user.role})
                </div>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="w-full text-left inline-flex items-center gap-2 text-sm font-medium text-destructive py-2"
                >
                  <LogOut className="w-4 h-4" />
                  Sign Out
                </button>
              </div>
            ) : (
              <div className="pt-2 border-t border-border space-y-2 px-3">
                <Link
                  to="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block text-center text-sm font-medium border border-border py-2 rounded-md hover:bg-secondary"
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block text-center text-sm font-medium bg-primary text-primary-foreground py-2 rounded-md shadow-sm"
                >
                  Register
                </Link>
              </div>
            )}
          </div>
        )}
      </PageContainer>
    </header>
  );
};
