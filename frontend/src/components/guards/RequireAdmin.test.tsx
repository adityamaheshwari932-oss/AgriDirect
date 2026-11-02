import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { RequireAdmin } from "./RequireAdmin";
import { authStore } from "../../store/authStore";
import { InMemoryTokenStorage, tokenStorage } from "../../api/tokenStorage";
import type { User } from "../../types";

const renderWithRouter = (initialRoute: string) => {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <Routes>
        <Route path="/login" element={<div>Login Page</div>} />
        <Route path="/dashboard/farmer" element={<div>Farmer Dashboard</div>} />
        <Route path="/dashboard/buyer" element={<div>Buyer Dashboard</div>} />
        <Route path="/" element={<div>Public Home</div>} />
        <Route
          path="/admin/users"
          element={
            <RequireAdmin>
              <div>Admin User Directory Protected Content</div>
            </RequireAdmin>
          }
        />
      </Routes>
    </MemoryRouter>
  );
};

describe("RequireAdmin Guard", () => {
  const baseUser: User = {
    id: "usr-1",
    email: "user@agridirect.test",
    role: "farmer",
    verification_status: "verified",
    account_status: "active",
    created_at: "2026-10-30T10:00:00Z",
    updated_at: "2026-10-30T10:00:00Z",
  };

  beforeEach(() => {
    tokenStorage.setProvider(new InMemoryTokenStorage());
    authStore.reset();
  });

  it("shows session verification spinner while authentication state is restoring", () => {
    authStore["state"] = {
      status: "restoring",
      user: null,
      error: null,
    };

    renderWithRouter("/admin/users");

    expect(
      screen.getByLabelText("Verifying administrative privileges")
    ).toBeInTheDocument();
    expect(
      screen.getByText(/verifying administrator authorization/i)
    ).toBeInTheDocument();
  });

  it("redirects unauthenticated user to /login", () => {
    authStore.logout();

    renderWithRouter("/admin/users");

    expect(screen.getByText("Login Page")).toBeInTheDocument();
    expect(
      screen.queryByText("Admin User Directory Protected Content")
    ).not.toBeInTheDocument();
  });

  it("blocks farmer user and redirects to farmer dashboard", () => {
    authStore["state"] = {
      status: "authenticated",
      user: { ...baseUser, role: "farmer" },
      error: null,
    };

    renderWithRouter("/admin/users");

    expect(screen.getByText("Farmer Dashboard")).toBeInTheDocument();
    expect(
      screen.queryByText("Admin User Directory Protected Content")
    ).not.toBeInTheDocument();
  });

  it("blocks buyer user and redirects to buyer dashboard", () => {
    authStore["state"] = {
      status: "authenticated",
      user: { ...baseUser, role: "buyer" },
      error: null,
    };

    renderWithRouter("/admin/users");

    expect(screen.getByText("Buyer Dashboard")).toBeInTheDocument();
    expect(
      screen.queryByText("Admin User Directory Protected Content")
    ).not.toBeInTheDocument();
  });

  it("grants access to authenticated administrator and renders content", () => {
    authStore["state"] = {
      status: "authenticated",
      user: { ...baseUser, role: "admin", email: "admin@agridirect.gov" },
      error: null,
    };

    renderWithRouter("/admin/users");

    expect(
      screen.getByText("Admin User Directory Protected Content")
    ).toBeInTheDocument();
  });
});

