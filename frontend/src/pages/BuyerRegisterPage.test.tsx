import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BuyerRegisterPage } from "./BuyerRegisterPage";
import { authStore } from "../store/authStore";
import { ApiError } from "../api/errors";
import { InMemoryTokenStorage, tokenStorage } from "../api/tokenStorage";
import type { User } from "../types";

describe("BuyerRegisterPage", () => {
  const mockRegisteredBuyer: User = {
    id: "buyer-uuid-456",
    email: "procurement@grandhotel.test",
    role: "buyer",
    verification_status: "pending",
    account_status: "active",
    created_at: "2026-10-29T12:00:00Z",
    updated_at: "2026-10-29T12:00:00Z",
    buyer_profile: {
      id: "profile-uuid-2",
      contact_person_name: "Rahul Verma",
      business_name: "Grand Hotel & Dining",
      business_type: "hotel",
      business_registration_number: "27AAAAA0000A1Z5",
      delivery_receiving_address: "Dock 4, Industrial Area",
      city: "Mumbai",
      state: "Maharashtra",
      postal_code: "400001",
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
        <BuyerRegisterPage />
      </MemoryRouter>
    );
  };

  it("renders all required and optional registration fields and submit button", () => {
    renderComponent();

    expect(screen.getByLabelText(/contact person name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/commercial email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/commercial entity type/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();

    // Business entity details
    expect(screen.getByLabelText(/registered business \/ trade name/i)).toBeInTheDocument();
    expect(
      screen.getByLabelText(/tax \/ business registration id/i)
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/contact phone/i)).toBeInTheDocument();
    expect(
      screen.getByLabelText(/receiving dock \/ delivery address/i)
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/city/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/state \/ province/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/postal code/i)).toBeInTheDocument();
    expect(
      screen.getByLabelText(/procurement overview & produce interests/i)
    ).toBeInTheDocument();

    expect(
      screen.getByRole("button", { name: /complete commercial buyer registration/i })
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /^sign in$/i })).toBeInTheDocument();
  });

  it("populates business type dropdown with all 7 backend-supported types", () => {
    renderComponent();

    const select = screen.getByLabelText(/commercial entity type/i) as HTMLSelectElement;
    const options = Array.from(select.options).map((opt) => opt.value);

    expect(options).toEqual([
      "restaurant",
      "hotel",
      "retailer",
      "wholesaler",
      "food_processor",
      "caterer",
      "other",
    ]);
  });

  it("validates client-side required fields on empty submission", async () => {
    renderComponent();

    fireEvent.click(
      screen.getByRole("button", { name: /complete commercial buyer registration/i })
    );

    expect(await screen.findByText(/contact person name is required/i)).toBeInTheDocument();
    expect(await screen.findByText(/email address is required/i)).toBeInTheDocument();
    expect(await screen.findByText(/^password is required\./i)).toBeInTheDocument();
    expect(await screen.findByText(/please confirm your password/i)).toBeInTheDocument();
  });

  it("rejects invalid email formats", async () => {
    const user = userEvent.setup();
    renderComponent();

    await user.type(screen.getByLabelText(/contact person name/i), "Rahul Verma");
    await user.type(screen.getByLabelText(/commercial email/i), "invalid-format");
    await user.type(screen.getByLabelText(/^password/i), "SecretPass123!");
    await user.type(screen.getByLabelText(/confirm password/i), "SecretPass123!");
    await user.click(
      screen.getByRole("button", { name: /complete commercial buyer registration/i })
    );

    expect(await screen.findByText(/please enter a valid email address/i)).toBeInTheDocument();
  });

  it("rejects passwords under 8 characters", async () => {
    const user = userEvent.setup();
    renderComponent();

    await user.type(screen.getByLabelText(/contact person name/i), "Rahul Verma");
    await user.type(screen.getByLabelText(/commercial email/i), "buyer@hotel.test");
    await user.type(screen.getByLabelText(/^password/i), "short7");
    await user.type(screen.getByLabelText(/confirm password/i), "short7");
    await user.click(
      screen.getByRole("button", { name: /complete commercial buyer registration/i })
    );

    expect(
      await screen.findByText(/password must be at least 8 characters long/i)
    ).toBeInTheDocument();
  });

  it("rejects mismatched passwords", async () => {
    const user = userEvent.setup();
    renderComponent();

    await user.type(screen.getByLabelText(/contact person name/i), "Rahul Verma");
    await user.type(screen.getByLabelText(/commercial email/i), "buyer@hotel.test");
    await user.type(screen.getByLabelText(/^password/i), "SecretPass123!");
    await user.type(screen.getByLabelText(/confirm password/i), "DifferentPass999!");
    await user.click(
      screen.getByRole("button", { name: /complete commercial buyer registration/i })
    );

    expect(await screen.findByText(/passwords do not match/i)).toBeInTheDocument();
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

  it("successfully registers a commercial buyer and renders confirmation view without auto-login", async () => {
    const user = userEvent.setup();
    const registerSpy = vi
      .spyOn(authStore, "registerBuyer")
      .mockResolvedValueOnce(mockRegisteredBuyer);

    renderComponent();

    await user.type(screen.getByLabelText(/contact person name/i), "Rahul Verma");
    await user.type(screen.getByLabelText(/commercial email/i), "procurement@grandhotel.test");
    await user.selectOptions(screen.getByLabelText(/commercial entity type/i), "hotel");
    await user.type(screen.getByLabelText(/^password/i), "SecurePass123!");
    await user.type(screen.getByLabelText(/confirm password/i), "SecurePass123!");
    await user.type(
      screen.getByLabelText(/registered business \/ trade name/i),
      "Grand Hotel & Dining"
    );
    await user.type(
      screen.getByLabelText(/tax \/ business registration id/i),
      "27AAAAA0000A1Z5"
    );
    await user.type(screen.getByLabelText(/city/i), "Mumbai");
    await user.type(screen.getByLabelText(/state \/ province/i), "Maharashtra");

    await user.click(
      screen.getByRole("button", { name: /complete commercial buyer registration/i })
    );

    await waitFor(() => {
      expect(registerSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          contact_person_name: "Rahul Verma",
          full_name: "Rahul Verma",
          email: "procurement@grandhotel.test",
          password: "SecurePass123!",
          password_confirm: "SecurePass123!",
          business_type: "hotel",
          business_name: "Grand Hotel & Dining",
          business_registration_number: "27AAAAA0000A1Z5",
          city: "Mumbai",
          state: "Maharashtra",
        })
      );
    });

    // Check post-registration success view
    expect(await screen.findByText(/commercial account created/i)).toBeInTheDocument();
    expect(screen.getByText(/Welcome, Rahul Verma!/i)).toBeInTheDocument();
    expect(screen.getByText(/pending/i)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /sign in to your account/i })
    ).toHaveAttribute("href", "/login");
  });

  it("handles duplicate account conflict (HTTP 409)", async () => {
    const user = userEvent.setup();
    vi.spyOn(authStore, "registerBuyer").mockRejectedValueOnce(
      new ApiError(409, "A user with this email or phone number already exists.")
    );

    renderComponent();

    await user.type(screen.getByLabelText(/contact person name/i), "Rahul Verma");
    await user.type(screen.getByLabelText(/commercial email/i), "existing@hotel.test");
    await user.type(screen.getByLabelText(/^password/i), "SecurePass123!");
    await user.type(screen.getByLabelText(/confirm password/i), "SecurePass123!");
    await user.click(
      screen.getByRole("button", { name: /complete commercial buyer registration/i })
    );

    expect(
      await screen.findByText(/a user with this email or phone number already exists/i)
    ).toBeInTheDocument();
  });

  it("handles backend validation errors (HTTP 422) and maps field errors", async () => {
    const user = userEvent.setup();
    vi.spyOn(authStore, "registerBuyer").mockRejectedValueOnce(
      new ApiError(422, "Validation error", [
        {
          loc: ["body", "business_registration_number"],
          msg: "Registration number already on file",
          type: "value_error",
        },
      ])
    );

    renderComponent();

    await user.type(screen.getByLabelText(/contact person name/i), "Rahul Verma");
    await user.type(screen.getByLabelText(/commercial email/i), "buyer@hotel.test");
    await user.type(screen.getByLabelText(/^password/i), "SecurePass123!");
    await user.type(screen.getByLabelText(/confirm password/i), "SecurePass123!");
    await user.click(
      screen.getByRole("button", { name: /complete commercial buyer registration/i })
    );

    expect(
      await screen.findByText(/validation error: please check the highlighted fields/i)
    ).toBeInTheDocument();
    expect(
      await screen.findByText(/registration number already on file/i)
    ).toBeInTheDocument();
  });

  it("handles network error gracefully (status 0)", async () => {
    const user = userEvent.setup();
    vi.spyOn(authStore, "registerBuyer").mockRejectedValueOnce(
      new ApiError(0, "Network error: Unable to reach the server. Please check your connection.")
    );

    renderComponent();

    await user.type(screen.getByLabelText(/contact person name/i), "Rahul Verma");
    await user.type(screen.getByLabelText(/commercial email/i), "buyer@hotel.test");
    await user.type(screen.getByLabelText(/^password/i), "SecurePass123!");
    await user.type(screen.getByLabelText(/confirm password/i), "SecurePass123!");
    await user.click(
      screen.getByRole("button", { name: /complete commercial buyer registration/i })
    );

    expect(
      await screen.findByText(/network error: unable to reach the server/i)
    ).toBeInTheDocument();
  });

  it("clears field error when user modifies that field", async () => {
    renderComponent();

    fireEvent.click(
      screen.getByRole("button", { name: /complete commercial buyer registration/i })
    );
    expect(await screen.findByText(/contact person name is required/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/contact person name/i), {
      target: { name: "contact_person_name", value: "Pooja Mehta" },
    });

    expect(screen.queryByText(/contact person name is required/i)).not.toBeInTheDocument();
  });
});
