import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LoginPage } from "./LoginPage";
import { authStore } from "../store/authStore";
import { ApiError } from "../api/errors";
import { InMemoryTokenStorage, tokenStorage } from "../api/tokenStorage";
import type { User } from "../types";

describe("LoginPage", () => {
  const mockUser: User = {
    id: "user-123",
    email: "test@example.com",
    role: "farmer",
    verification_status: "verified",
    account_status: "active",
    created_at: "2026-10-29T12:00:00Z",
    updated_at: "2026-10-29T12:00:00Z",
  };

  beforeEach(() => {
    tokenStorage.setProvider(new InMemoryTokenStorage());
    authStore.reset();
  });

  const renderComponent = () => {
    return render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );
  };

  it("renders email and password inputs and submit button", () => {
    renderComponent();

    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^sign in$/i })).toBeInTheDocument();
  });

  it("rejects empty fields with client-side validation errors", async () => {
    renderComponent();

    fireEvent.click(screen.getByRole("button", { name: /^sign in$/i }));

    expect(await screen.findByText(/email address is required/i)).toBeInTheDocument();
    expect(await screen.findByText(/password is required/i)).toBeInTheDocument();
  });

  it("rejects invalid email formats", async () => {
    const user = userEvent.setup();
    renderComponent();

    await user.type(screen.getByLabelText(/email address/i), "not-an-email");
    await user.type(screen.getByLabelText(/^password$/i), "ValidPassword123!");
    await user.click(screen.getByRole("button", { name: /^sign in$/i }));

    expect(await screen.findByText(/please enter a valid email address/i)).toBeInTheDocument();
  });

  it("toggles password visibility with accessible button", async () => {
    const user = userEvent.setup();
    renderComponent();

    const passwordInput = screen.getByLabelText(/^password$/i);
    expect(passwordInput).toHaveAttribute("type", "password");

    const toggleButton = screen.getByRole("button", { name: /show password/i });
    await user.click(toggleButton);

    expect(passwordInput).toHaveAttribute("type", "text");
    expect(screen.getByRole("button", { name: /hide password/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /hide password/i }));
    expect(passwordInput).toHaveAttribute("type", "password");
  });

  it("submits valid credentials and updates store on success", async () => {
    const user = userEvent.setup();
    const loginSpy = vi.spyOn(authStore, "login").mockResolvedValueOnce(mockUser);

    renderComponent();

    await user.type(screen.getByLabelText(/email address/i), "farmer@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "Secret123!");
    await user.click(screen.getByRole("button", { name: /^sign in$/i }));

    await waitFor(() => {
      expect(loginSpy).toHaveBeenCalledWith({
        email: "farmer@example.com",
        password: "Secret123!",
      });
    });
  });

  it("displays rate limiting error (429)", async () => {
    const user = userEvent.setup();
    vi.spyOn(authStore, "login").mockRejectedValueOnce(
      new ApiError(429, "Too many requests. Please try again later.")
    );

    renderComponent();

    await user.type(screen.getByLabelText(/email address/i), "farmer@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "Secret123!");
    await user.click(screen.getByRole("button", { name: /^sign in$/i }));

    expect(
      await screen.findByText(/too many login attempts/i)
    ).toBeInTheDocument();
  });

  it("displays invalid credentials error (401)", async () => {
    const user = userEvent.setup();
    vi.spyOn(authStore, "login").mockRejectedValueOnce(
      new ApiError(401, "Invalid email or password")
    );

    renderComponent();

    await user.type(screen.getByLabelText(/email address/i), "farmer@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "WrongPass123!");
    await user.click(screen.getByRole("button", { name: /^sign in$/i }));

    expect(await screen.findByText(/invalid email or password/i)).toBeInTheDocument();
  });

  it("displays suspended account error (403)", async () => {
    const user = userEvent.setup();
    vi.spyOn(authStore, "login").mockRejectedValueOnce(
      new ApiError(403, "Account is suspended or restricted")
    );

    renderComponent();

    await user.type(screen.getByLabelText(/email address/i), "suspended@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "Password123!");
    await user.click(screen.getByRole("button", { name: /^sign in$/i }));

    expect(await screen.findByText(/this account is suspended or restricted/i)).toBeInTheDocument();
  });

  it("displays network failure error cleanly without getting stuck in loading state", async () => {
    const user = userEvent.setup();
    vi.spyOn(authStore, "login").mockRejectedValueOnce(
      new ApiError(0, "Network error: Failed to fetch")
    );

    renderComponent();

    await user.type(screen.getByLabelText(/email address/i), "farmer@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "Password123!");
    await user.click(screen.getByRole("button", { name: /^sign in$/i }));

    expect(await screen.findByText(/unable to connect to the server/i)).toBeInTheDocument();
    // Submit button re-enabled
    expect(screen.getByRole("button", { name: /^sign in$/i })).not.toBeDisabled();
  });

  it("does not leak passwords in rendered errors", async () => {
    const user = userEvent.setup();
    vi.spyOn(authStore, "login").mockRejectedValueOnce(
      new ApiError(401, "Invalid credentials")
    );

    renderComponent();

    await user.type(screen.getByLabelText(/email address/i), "user@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "SuperSecretPassword123!");
    await user.click(screen.getByRole("button", { name: /^sign in$/i }));

    const errorAlert = await screen.findByRole("alert");
    expect(errorAlert.textContent).not.toContain("SuperSecretPassword123!");
  });
});
