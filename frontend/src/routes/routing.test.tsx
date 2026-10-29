import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { AppLayout } from "../components/layout";
import { GuestOnly, RequireAuth } from "../components/guards";
import {
  LandingPage,
  LoginPage,
  RegisterRolePage,
  FarmerRegisterPage,
  BuyerRegisterPage,
  NotFoundPage,
  ProtectedPlaceholderPage,
} from "../pages";
import { authStore } from "../store/authStore";
import { InMemoryTokenStorage, tokenStorage } from "../api/tokenStorage";
import { getSafeRedirectUrl } from "../utils/redirect";
import type { User } from "../types";

const renderWithRouter = (initialRoute: string) => {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<LandingPage />} />
          <Route
            path="/login"
            element={
              <GuestOnly>
                <LoginPage />
              </GuestOnly>
            }
          />
          <Route
            path="/register"
            element={
              <GuestOnly>
                <RegisterRolePage />
              </GuestOnly>
            }
          />
          <Route
            path="/register/farmer"
            element={
              <GuestOnly>
                <FarmerRegisterPage />
              </GuestOnly>
            }
          />
          <Route
            path="/register/buyer"
            element={
              <GuestOnly>
                <BuyerRegisterPage />
              </GuestOnly>
            }
          />
          <Route
            path="/protected-test"
            element={
              <RequireAuth>
                <ProtectedPlaceholderPage />
              </RequireAuth>
            }
          />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
};

describe("Routing and Route Guards", () => {
  const mockUser: User = {
    id: "user-123",
    email: "farmer@example.com",
    role: "farmer",
    verification_status: "verified",
    account_status: "active",
    created_at: "2026-10-29T12:00:00Z",
    updated_at: "2026-10-29T12:00:00Z",
  };

  beforeEach(() => {
    tokenStorage.setProvider(new InMemoryTokenStorage());
    authStore.reset();
    authStore.logout(); // Sets status: "unauthenticated" representing verified guest state
  });

  it("renders public landing page at '/'", () => {
    renderWithRouter("/");
    expect(
      screen.getByText("Connecting Farmers Directly with Commercial Buyers")
    ).toBeInTheDocument();
  });

  it("renders login page at '/login'", () => {
    renderWithRouter("/login");
    expect(screen.getByRole("heading", { name: /sign in to your account/i })).toBeInTheDocument();
  });

  it("renders role selection at '/register'", () => {
    renderWithRouter("/register");
    expect(screen.getByRole("heading", { name: /create your agridirect account/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /^agricultural producer$/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /^commercial buyer$/i })).toBeInTheDocument();
  });

  it("renders farmer registration at '/register/farmer'", () => {
    renderWithRouter("/register/farmer");
    expect(screen.getByRole("heading", { name: /farmer account registration/i })).toBeInTheDocument();
  });

  it("renders buyer registration at '/register/buyer'", () => {
    renderWithRouter("/register/buyer");
    expect(screen.getByRole("heading", { name: /commercial buyer registration/i })).toBeInTheDocument();
  });

  it("renders 404 page for unknown routes", () => {
    renderWithRouter("/some-random-unknown-page");
    expect(screen.getByRole("heading", { name: /404 — page not found/i })).toBeInTheDocument();
  });

  it("redirects unauthenticated user from protected route to '/login'", () => {
    authStore.logout();
    renderWithRouter("/protected-test");

    // RequireAuth redirects unauthenticated user to login
    expect(screen.getByRole("heading", { name: /sign in to your account/i })).toBeInTheDocument();
  });

  it("shows loading indicator on protected route while session is uninitialized", () => {
    authStore.reset(); // status: "uninitialized"
    renderWithRouter("/protected-test");

    expect(screen.getByText(/verifying session\.\.\./i)).toBeInTheDocument();
  });

  it("shows loading indicator on protected route while session restoration is in progress", () => {
    authStore["state"] = {
      status: "restoring",
      user: null,
      error: null,
    };

    renderWithRouter("/protected-test");

    expect(screen.getByText(/verifying session\.\.\./i)).toBeInTheDocument();
  });

  it("renders protected content when user is authenticated", () => {
    authStore["state"] = {
      status: "authenticated",
      user: mockUser,
      error: null,
    };

    renderWithRouter("/protected-test");

    expect(
      screen.getByRole("heading", { name: /protected route verification placeholder/i })
    ).toBeInTheDocument();
    expect(screen.getAllByText(/farmer@example\.com/)[0]).toBeInTheDocument();
  });

  it("redirects authenticated user away from guest-only login route", () => {
    authStore["state"] = {
      status: "authenticated",
      user: mockUser,
      error: null,
    };

    renderWithRouter("/login");

    // GuestOnly redirects to fallback "/"
    expect(
      screen.getByText("Connecting Farmers Directly with Commercial Buyers")
    ).toBeInTheDocument();
  });

  it("rejects open redirects and external URLs in getSafeRedirectUrl", () => {
    expect(getSafeRedirectUrl("https://evil.com")).toBe("/");
    expect(getSafeRedirectUrl("//evil.com")).toBe("/");
    expect(getSafeRedirectUrl("javascript:alert(1)")).toBe("/");
    expect(getSafeRedirectUrl("")).toBe("/");
    expect(getSafeRedirectUrl(null)).toBe("/");

    // Valid relative internal paths
    expect(getSafeRedirectUrl("/protected-test")).toBe("/protected-test");
    expect(getSafeRedirectUrl("/register/farmer?ref=partner")).toBe("/register/farmer?ref=partner");
  });
});
