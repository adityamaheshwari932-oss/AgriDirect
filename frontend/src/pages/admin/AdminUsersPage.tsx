import React, { useEffect, useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import {
  Users,
  Search,
  Eye,
  ShieldAlert,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
} from "lucide-react";
import { adminApi } from "../../api/admin";
import { useAuth } from "../../store/authStore";
import type { AdminUserFilterParams, AdminUserSummary } from "../../types/admin";
import { LoadingState, ErrorState, EmptyState } from "../../components/ui/states";
import { AdminUserDetailModal } from "../../components/admin/AdminUserDetailModal";
import { AdminUserStatusModal } from "../../components/admin/AdminUserStatusModal";
import { formatDate } from "../../utils/formatters";

export const AdminUsersPage: React.FC = () => {
  const { t } = useTranslation(["admin", "common"]);
  const { user: currentAdmin } = useAuth();

  const [users, setUsers] = useState<AdminUserSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 15;
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [verificationFilter, setVerificationFilter] = useState("");
  const [registeredFrom, setRegisteredFrom] = useState("");
  const [registeredTo, setRegisteredTo] = useState("");
  const [sortBy, setSortBy] = useState("created_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  // Modals state
  const [selectedDetailUserId, setSelectedDetailUserId] = useState<string | null>(null);
  const [selectedStatusUser, setSelectedStatusUser] = useState<AdminUserSummary | null>(null);

  const fetchUsers = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params: AdminUserFilterParams = {
        page,
        page_size: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      };
      if (search.trim()) params.search = search.trim();
      if (roleFilter) params.role = roleFilter;
      if (statusFilter) params.account_status = statusFilter;
      if (verificationFilter) params.verification_status = verificationFilter;
      if (registeredFrom) params.registered_from = registeredFrom;
      if (registeredTo) params.registered_to = registeredTo;

      const res = await adminApi.listUsers(params);
      setUsers(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages || 1);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t("admin:load_error", "Failed to load user directory.");
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [
    page,
    pageSize,
    search,
    roleFilter,
    statusFilter,
    verificationFilter,
    registeredFrom,
    registeredTo,
    sortBy,
    sortOrder,
    t,
  ]);

  useEffect(() => {
    void fetchUsers();
  }, [fetchUsers]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    void fetchUsers();
  };

  const renderAccountBadge = (status: string) => {
    switch (status) {
      case "active":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-700 border border-emerald-500/20">
            {t("common:status.active", "Active")}
          </span>
        );
      case "restricted":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-700 border border-amber-500/20">
            {t("admin:status_restricted", "Restricted")}
          </span>
        );
      case "suspended":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-500/10 text-red-700 border border-red-500/20">
            {t("admin:status_suspended", "Suspended")}
          </span>
        );
      case "blocked":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-destructive text-destructive-foreground">
            {t("admin:status_blocked", "Blocked")}
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-secondary text-foreground capitalize">
            {status}
          </span>
        );
    }
  };

  const renderVerificationBadge = (status: string) => {
    switch (status) {
      case "verified":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
            <ShieldCheck className="w-3 h-3 text-emerald-600" />
            {t("common:status.verified", "Verified")}
          </span>
        );
      case "pending":
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-blue-100 text-blue-800 border border-blue-200">
            {t("common:status.pending", "Pending")}
          </span>
        );
      case "rejected":
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-rose-100 text-rose-800 border border-rose-200">
            {t("common:status.rejected", "Rejected")}
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-secondary text-muted-foreground">
            {t("common:status.unverified", "Unverified")}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
          <Users className="w-6 h-6 text-primary" aria-hidden="true" />
          <span>{t("admin:users_directory_title", "User Directory & Moderation")}</span>
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          {t("admin:users_directory_subtitle", "Inspect platform trade accounts, manage moderation statuses, and enforce governance rules.")}
        </p>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-2xl bg-card border border-border shadow-xs space-y-3">
        <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-muted-foreground absolute start-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t("admin:search_placeholder", "Search by email, name, phone, or business name...")}
              className="w-full ps-9 pe-3 py-2 text-xs rounded-xl border border-border bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-colors shadow-xs shrink-0"
          >
            {t("admin:search_directory", "Search Directory")}
          </button>
        </form>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 pt-2 border-t border-border text-xs">
          {/* Role Filter */}
          <div>
            <label className="text-[10px] uppercase font-bold text-muted-foreground block mb-1">
              {t("common:labels.role", "Role")}
            </label>
            <select
              value={roleFilter}
              onChange={(e) => {
                setRoleFilter(e.target.value);
                setPage(1);
              }}
              className="w-full px-2.5 py-1.5 rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="">{t("admin:filter_all_roles", "All Roles")}</option>
              <option value="farmer">{t("common:roles.farmer", "Farmer")}</option>
              <option value="buyer">{t("common:roles.buyer", "Buyer")}</option>
              <option value="admin">{t("common:roles.admin", "Administrator")}</option>
            </select>
          </div>

          {/* Account Status Filter */}
          <div>
            <label className="text-[10px] uppercase font-bold text-muted-foreground block mb-1">
              {t("common:labels.status", "Account Status")}
            </label>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="w-full px-2.5 py-1.5 rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="">{t("admin:filter_all_statuses", "All Statuses")}</option>
              <option value="active">{t("common:status.active", "Active")}</option>
              <option value="restricted">{t("admin:status_restricted", "Restricted")}</option>
              <option value="suspended">{t("admin:status_suspended", "Suspended")}</option>
              <option value="blocked">{t("admin:status_blocked", "Blocked")}</option>
            </select>
          </div>

          {/* Verification Status */}
          <div>
            <label className="text-[10px] uppercase font-bold text-muted-foreground block mb-1">
              {t("verification:title_short", "Verification")}
            </label>
            <select
              value={verificationFilter}
              onChange={(e) => {
                setVerificationFilter(e.target.value);
                setPage(1);
              }}
              className="w-full px-2.5 py-1.5 rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="">{t("admin:filter_all_verification", "All Verification")}</option>
              <option value="verified">{t("common:status.verified", "Verified")}</option>
              <option value="pending">{t("common:status.pending", "Pending")}</option>
              <option value="unverified">{t("common:status.unverified", "Unverified")}</option>
              <option value="rejected">{t("common:status.rejected", "Rejected")}</option>
            </select>
          </div>

          {/* Sort By */}
          <div>
            <label className="text-[10px] uppercase font-bold text-muted-foreground block mb-1">
              {t("admin:sort_by", "Sort By")}
            </label>
            <select
              value={`${sortBy}-${sortOrder}`}
              onChange={(e) => {
                const [sb, so] = e.target.value.split("-");
                setSortBy(sb);
                setSortOrder(so as "asc" | "desc");
                setPage(1);
              }}
              className="w-full px-2.5 py-1.5 rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="created_at-desc">{t("admin:sort_registered_newest", "Registered (Newest)")}</option>
              <option value="created_at-asc">{t("admin:sort_registered_oldest", "Registered (Oldest)")}</option>
              <option value="email-asc">{t("admin:sort_email_asc", "Email (A-Z)")}</option>
              <option value="email-desc">{t("admin:sort_email_desc", "Email (Z-A)")}</option>
              <option value="role-asc">{t("admin:sort_role_asc", "Role (A-Z)")}</option>
              <option value="account_status-asc">{t("admin:sort_status", "Status")}</option>
            </select>
          </div>

          {/* Registered From */}
          <div>
            <label className="text-[10px] uppercase font-bold text-muted-foreground block mb-1">
              {t("admin:registered_from", "Registered From")}
            </label>
            <input
              type="date"
              value={registeredFrom}
              onChange={(e) => {
                setRegisteredFrom(e.target.value);
                setPage(1);
              }}
              className="w-full px-2 py-1 rounded-lg border border-border bg-card text-foreground text-xs focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          {/* Registered To */}
          <div>
            <label className="text-[10px] uppercase font-bold text-muted-foreground block mb-1">
              {t("admin:registered_to", "Registered To")}
            </label>
            <input
              type="date"
              value={registeredTo}
              onChange={(e) => {
                setRegisteredTo(e.target.value);
                setPage(1);
              }}
              className="w-full px-2 py-1 rounded-lg border border-border bg-card text-foreground text-xs focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>
      </div>

      {/* Directory Table Area */}
      {error && <ErrorState message={error} onRetry={() => void fetchUsers()} />}

      {isLoading ? (
        <LoadingState message={t("admin:loading_users", "Loading platform users...")} />
      ) : users.length === 0 ? (
        <EmptyState
          title={t("admin:empty_users_title", "No users match the criteria")}
          description={t("admin:empty_users_desc", "Try adjusting your search queries or clearing active role/status filters.")}
        />
      ) : (
        <div className="bg-card border border-border rounded-2xl shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-start text-xs">
              <thead className="bg-secondary/40 text-muted-foreground font-semibold border-b border-border">
                <tr>
                  <th className="px-4 py-3">{t("admin:th_user_contact", "User & Contact")}</th>
                  <th className="px-4 py-3">{t("common:labels.role", "Role")}</th>
                  <th className="px-4 py-3">{t("admin:th_account_status", "Account Status")}</th>
                  <th className="px-4 py-3">{t("verification:title_short", "Verification")}</th>
                  <th className="px-4 py-3">{t("admin:th_org_location", "Organization / Location")}</th>
                  <th className="px-4 py-3">{t("admin:th_registered_date", "Registered Date")}</th>
                  <th className="px-4 py-3 text-end">{t("common:labels.actions", "Actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {users.map((u) => {
                  const isCurrentSelf = currentAdmin?.id === u.id;
                  return (
                    <tr key={u.id} className="hover:bg-secondary/20 transition-colors">
                      <td className="px-4 py-3">
                        <div className="font-semibold text-foreground flex items-center gap-1.5">
                          {u.display_name}
                          {isCurrentSelf && (
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-purple-100 text-purple-800 font-bold">
                              {t("common:labels.you", "You")}
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-muted-foreground font-mono">{u.email}</div>
                        {u.phone_number && (
                          <div className="text-[10px] text-muted-foreground">{u.phone_number}</div>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className="capitalize font-semibold text-foreground">{u.role}</span>
                      </td>
                      <td className="px-4 py-3">{renderAccountBadge(u.account_status)}</td>
                      <td className="px-4 py-3">{renderVerificationBadge(u.verification_status)}</td>
                      <td className="px-4 py-3 text-muted-foreground">
                        <div>{u.organization_name || "—"}</div>
                        {u.location_summary && (
                          <div className="text-[10px] text-muted-foreground/80">{u.location_summary}</div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">
                        {formatDate(u.created_at)}
                      </td>
                      <td className="px-4 py-3 text-end">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            type="button"
                            onClick={() => setSelectedDetailUserId(u.id)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-primary hover:bg-primary/10 font-semibold transition-colors"
                            aria-label={`Inspect user ${u.email}`}
                          >
                            <Eye className="w-3.5 h-3.5" />
                            <span>{t("admin:btn_inspect", "Inspect")}</span>
                          </button>

                          <button
                            type="button"
                            disabled={isCurrentSelf}
                            onClick={() => setSelectedStatusUser(u)}
                            title={
                              isCurrentSelf
                                ? "Self-modification forbidden: You cannot modify your own administrator account status."
                                : t("admin:moderate_account_status", "Moderate account status")
                            }
                            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors ${
                              isCurrentSelf
                                ? "opacity-40 cursor-not-allowed text-muted-foreground"
                                : "text-amber-700 hover:bg-amber-500/10"
                            }`}
                            aria-label={`Moderate status of user ${u.email}`}
                          >
                            <ShieldAlert className="w-3.5 h-3.5" />
                            <span>{t("admin:btn_status", "Status")}</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="px-4 py-3 border-t border-border flex items-center justify-between text-xs text-muted-foreground">
              <span>
                {t("common:pagination.showing_page", `Page ${page} of ${totalPages} (${total} users total)`, {
                  page,
                  totalPages,
                  count: total,
                })}
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="p-1.5 rounded-lg border border-border hover:bg-secondary disabled:opacity-40 transition-colors"
                  aria-label={t("common:pagination.previous", "Previous page")}
                >
                  <ChevronLeft className="w-4 h-4 rtl:rotate-180" />
                </button>
                <button
                  type="button"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                  className="p-1.5 rounded-lg border border-border hover:bg-secondary disabled:opacity-40 transition-colors"
                  aria-label={t("common:pagination.next", "Next page")}
                >
                  <ChevronRight className="w-4 h-4 rtl:rotate-180" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Modals */}
      <AdminUserDetailModal
        userId={selectedDetailUserId}
        isOpen={Boolean(selectedDetailUserId)}
        onClose={() => setSelectedDetailUserId(null)}
      />

      <AdminUserStatusModal
        user={selectedStatusUser}
        currentAdminId={currentAdmin?.id}
        isOpen={Boolean(selectedStatusUser)}
        onClose={() => setSelectedStatusUser(null)}
        onSuccess={() => void fetchUsers()}
      />
    </div>
  );
};

