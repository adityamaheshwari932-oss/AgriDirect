import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FarmerRegisterPage } from "./FarmerRegisterPage";
import { authStore } from "../store/authStore";
import { ApiError } from "../api/errors";
import { InMemoryTokenStorage, tokenStorage } from "../api/tokenStorage";
import type { User } from "../types";

describe("FarmerRegisterPage", () => {
  const mockRegisteredFarmer: User = {
    id: "farmer-uuid-123",
    email: "farmer@greenacres.test",
    role: "farmer",
    verification_status: "pending",
    account_status: "active",
    created_at: "2026-10-29T12:00:00Z",
    updated_at: "2026-10-29T12:00:00Z",
    farmer_profile: {
      id: "profile-uuid-1",
      full_name: "Sarah Jenkins",
      farm_name: "Green Acres Organic Farm",
      farm_location_address: "123 Farm Road",
      city: "Salinas",
      state: "CA",
      postal_code: "93901",
      farming_practices: "organic",
      created_at: "2026-10-29T12:00:00Z",
      updated_at: "2026-10-29T12:00:00Z",
    },
  };

  beforeEach(() => {
    tokenStorage.setProvider(new InMemoryTokenStorage());
    authStore.reset();
    vi.restoreAllMocks();
  });

  const renderComponent = () => {
    return render(
      <MemoryRouter>
        <FarmerRegisterPage />
      </MemoryRouter>
    );
  };

  it("renders all required and optional registration fields and navigation link", () => {
    renderComponent();

    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();

    // Farm details
    expect(screen.getByLabelText(/farm or enterprise name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/phone number/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/farm physical address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/city \/ nearest town/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/state \/ province/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/postal code/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/total land size \(acres\)/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/farming practices/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/primary crops/i)).toBeInTheDocument();

    expect(
      screen.getByRole("button", { name: /complete farmer registration/i })
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /^sign in$/i })).toBeInTheDocument();
  });

  it("validates client-side required fields on empty submission", async () => {
    renderComponent();

    fireEvent.click(
      screen.getByRole("button", { name: /complete farmer registration/i })
    );

    expect(await screen.findByText(/full name is required/i)).toBeInTheDocument();
    expect(await screen.findByText(/email address is required/i)).toBeInTheDocument();
    expect(await screen.findByText(/^password is required\./i)).toBeInTheDocument();
    expect(await screen.findByText(/please confirm your password/i)).toBeInTheDocument();
  });

  it("rejects invalid email formats", async () => {
    const user = userEvent.setup();
    renderComponent();

    await user.type(screen.getByLabelText(/full name/i), "Sarah Jenkins");
    await user.type(screen.getByLabelText(/email address/i), "notanemail");
    await user.type(screen.getByLabelText(/^password/i), "Secret123!");
    await user.type(screen.getByLabelText(/confirm password/i), "Secret123!");
    await user.click(
      screen.getByRole("button", { name: /complete farmer registration/i })
    );

    expect(await screen.findByText(/please enter a valid email address/i)).toBeInTheDocument();
  });

  it("rejects passwords under 8 characters", async () => {
    const user = userEvent.setup();
    renderComponent();

    await user.type(screen.getByLabelText(/full name/i), "Sarah Jenkins");
    await user.type(screen.getByLabelText(/email address/i), "farmer@test.com");
    await user.type(screen.getByLabelText(/^password/i), "short");
    await user.type(screen.getByLabelText(/confirm password/i), "short");
    await user.click(
      screen.getByRole("button", { name: /complete farmer registration/i })
    );

    expect(
      await screen.findByText(/password must be at least 8 characters long/i)
    ).toBeInTheDocument();
  });

  it("rejects mismatched passwords", async () => {
    const user = userEvent.setup();
    renderComponent();

    await user.type(screen.getByLabelText(/full name/i), "Sarah Jenkins");
    await user.type(screen.getByLabelText(/email address/i), "farmer@test.com");
    await user.type(screen.getByLabelText(/^password/i), "Password123!");
    await user.type(screen.getByLabelText(/confirm password/i), "Mismatch999!");
    await user.click(
      screen.getByRole("button", { name: /complete farmer registration/i })
    );

    expect(await screen.findByText(/passwords do not match/i)).toBeInTheDocument();
  });

  it("rejects non-positive farm size in acres", async () => {
    const user = userEvent.setup();
    renderComponent();

    await user.type(screen.getByLabelText(/full name/i), "Sarah Jenkins");
    await user.type(screen.getByLabelText(/email address/i), "farmer@test.com");
    await user.type(screen.getByLabelText(/^password/i), "Password123!");
    await user.type(screen.getByLabelText(/confirm password/i), "Password123!");
    await user.type(screen.getByLabelText(/total land size \(acres\)/i), "-10");
    await user.click(
      screen.getByRole("button", { name: /complete farmer registration/i })
    );

    expect(
      await screen.findByText(/farm size must be a positive number of acres/i)
    ).toBeInTheDocument();
  });

  it("toggles password and confirmation visibility", async () => {
    const user = userEvent.setup();
    renderComponent();

    const passwordInput = screen.getByLabelText(/^password/i);
    const confirmInput = screen.getByLabelText(/confirm password/i);

    expect(passwordInput).toHaveAttribute("type", "password");
    expect(confirmInput).toHaveAttribute("type", "password");

    const showPasswordBtn = screen.getByRole("button", { name: /^show password$/i });
    const showConfirmBtn = screen.getByRole("button", { name: /^show confirmation password$/i });

    await user.click(showPasswordBtn);
    expect(passwordInput).toHaveAttribute("type", "text");

    await user.click(showConfirmBtn);
    expect(confirmInput).toHaveAttribute("type", "text");

    const hidePasswordBtn = screen.getByRole("button", { name: /^hide password$/i });
    await user.click(hidePasswordBtn);
    expect(passwordInput).toHaveAttribute("type", "password");
  });

  it("successfully registers a farmer and renders confirmation view without auto-login", async () => {
    const user = userEvent.setup();
    const registerSpy = vi
      .spyOn(authStore, "registerFarmer")
      .mockResolvedValueOnce(mockRegisteredFarmer);

    renderComponent();

    await user.type(screen.getByLabelText(/full name/i), "Sarah Jenkins");
    await user.type(screen.getByLabelText(/email address/i), "farmer@greenacres.test");
    await user.type(screen.getByLabelText(/^password/i), "Password123!");
    await user.type(screen.getByLabelText(/confirm password/i), "Password123!");
    await user.type(screen.getByLabelText(/farm or enterprise name/i), "Green Acres Organic Farm");
    await user.type(screen.getByLabelText(/phone number/i), "+15551234567");
    await user.type(screen.getByLabelText(/total land size \(acres\)/i), "45.5");
    await user.type(screen.getByLabelText(/primary crops/i), "Organic Heirloom Tomatoes, Basil");

    await user.click(
      screen.getByRole("button", { name: /complete farmer registration/i })
    );

    await waitFor(() => {
      expect(registerSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          full_name: "Sarah Jenkins",
          email: "farmer@greenacres.test",
          password: "Password123!",
          password_confirm: "Password123!",
          farm_name: "Green Acres Organic Farm",
          phone_number: "+15551234567",
          farm_size_acres: 45.5,
          primary_crops: "Organic Heirloom Tomatoes, Basil",
        })
      );
    });

    // Check post-registration success view
    expect(await screen.findByText(/account created successfully/i)).toBeInTheDocument();
    expect(screen.getByText(/Welcome, Sarah Jenkins!/i)).toBeInTheDocument();
    expect(screen.getByText(/pending/i)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /sign in to your account/i })
    ).toHaveAttribute("href", "/login");
  });

  it("handles duplicate account conflict (HTTP 409)", async () => {
    const user = userEvent.setup();
    vi.spyOn(authStore, "registerFarmer").mockRejectedValueOnce(
      new ApiError(409, "A user with this email or phone number already exists.")
    );

    renderComponent();

    await user.type(screen.getByLabelText(/full name/i), "Duplicate User");
    await user.type(screen.getByLabelText(/email address/i), "existing@example.com");
    await user.type(screen.getByLabelText(/^password/i), "Password123!");
    await user.type(screen.getByLabelText(/confirm password/i), "Password123!");
    await user.click(
      screen.getByRole("button", { name: /complete farmer registration/i })
    );

    expect(
      await screen.findByText(/a user with this email or phone number already exists/i)
    ).toBeInTheDocument();
  });

  it("handles backend validation errors (HTTP 422) and maps field errors", async () => {
    const user = userEvent.setup();
    vi.spyOn(authStore, "registerFarmer").mockRejectedValueOnce(
      new ApiError(422, "Validation error", [
        {
          loc: ["body", "phone_number"],
          msg: "Invalid international phone format",
          type: "value_error",
        },
      ])
    );

    renderComponent();

    await user.type(screen.getByLabelText(/full name/i), "Sarah Jenkins");
    await user.type(screen.getByLabelText(/email address/i), "farmer@test.com");
    await user.type(screen.getByLabelText(/^password/i), "Password123!");
    await user.type(screen.getByLabelText(/confirm password/i), "Password123!");
    await user.click(
      screen.getByRole("button", { name: /complete farmer registration/i })
    );

    expect(
      await screen.findByText(/validation error: please check the highlighted fields/i)
    ).toBeInTheDocument();
    expect(
      await screen.findByText(/invalid international phone format/i)
    ).toBeInTheDocument();
  });

  it("handles network error gracefully (status 0)", async () => {
    const user = userEvent.setup();
    vi.spyOn(authStore, "registerFarmer").mockRejectedValueOnce(
      new ApiError(0, "Network error: Unable to reach the server. Please check your connection.")
    );

    renderComponent();

    await user.type(screen.getByLabelText(/full name/i), "Sarah Jenkins");
    await user.type(screen.getByLabelText(/email address/i), "farmer@test.com");
    await user.type(screen.getByLabelText(/^password/i), "Password123!");
    await user.type(screen.getByLabelText(/confirm password/i), "Password123!");
    await user.click(
      screen.getByRole("button", { name: /complete farmer registration/i })
    );

    expect(
      await screen.findByText(/network error: unable to reach the server/i)
    ).toBeInTheDocument();
  });

  it("clears field error when user modifies that field", async () => {
    renderComponent();

    fireEvent.click(
      screen.getByRole("button", { name: /complete farmer registration/i })
    );
    expect(await screen.findByText(/full name is required/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/full name/i), {
      target: { name: "full_name", value: "Farmer John" },
    });

    expect(screen.queryByText(/full name is required/i)).not.toBeInTheDocument();
  });
});
