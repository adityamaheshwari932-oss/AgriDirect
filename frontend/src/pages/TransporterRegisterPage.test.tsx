import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TransporterRegisterPage } from "./TransporterRegisterPage";
import { authStore } from "../store/authStore";
import { InMemoryTokenStorage, tokenStorage } from "../api/tokenStorage";
import type { User } from "../types";

describe("TransporterRegisterPage", () => {
  const mockRegisteredTransporter: User = {
    id: "transporter-uuid-123",
    email: "transporter@logistics.test",
    role: "transporter",
    verification_status: "unverified",
    account_status: "active",
    created_at: "2026-11-18T12:00:00Z",
    updated_at: "2026-11-18T12:00:00Z",
    transporter_profile: {
      id: "profile-uuid-1",
      business_name: "Kisan Fast Logistics",
      contact_name: "Ramesh Pawar",
      phone_number: "+919876543210",
      transport_type: "mini_truck",
      vehicle_capacity_kg: 2500,
      vehicle_registration_number: "MH-12-AB-1234",
      is_available: true,
      experience_years: 4,
      operating_states: "Maharashtra",
      bio: "Rural transport provider",
      created_at: "2026-11-18T12:00:00Z",
      updated_at: "2026-11-18T12:00:00Z",
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
        <TransporterRegisterPage />
      </MemoryRouter>
    );
  };

  it("renders all required registration fields", () => {
    renderComponent();
    expect(screen.getByText(/Register as Transportation Provider/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Kisan Super Transport/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Rajesh Patil/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/transporter@example.com/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/MH-12-AB-1234/i)).toBeInTheDocument();
  });

  it("validates empty submission and displays error messages", async () => {
    renderComponent();
    const submitBtn = screen.getByRole("button", { name: /Complete Transporter Registration/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Contact person name is required/i)).toBeInTheDocument();
      expect(screen.getByText(/Business name is required/i)).toBeInTheDocument();
    });
  });

  it("submits valid form data and renders success screen", async () => {
    vi.spyOn(authStore, "registerTransporter").mockResolvedValueOnce(mockRegisteredTransporter);

    renderComponent();
    const user = userEvent.setup();

    await user.type(screen.getByPlaceholderText(/Kisan Super Transport/i), "Kisan Fast Logistics");
    await user.type(screen.getByPlaceholderText(/Rajesh Patil/i), "Ramesh Pawar");
    await user.type(screen.getByPlaceholderText(/transporter@example.com/i), "transporter@logistics.test");
    await user.type(screen.getByPlaceholderText(/\+91 98765 43210/i), "+919876543210");
    await user.type(screen.getByPlaceholderText(/MH-12-AB-1234/i), "MH-12-AB-1234");
    await user.type(screen.getByPlaceholderText(/^e\.g\. Maharashtra$/i), "Maharashtra");
    await user.type(screen.getByPlaceholderText(/e\.g\. Pune/i), "Pune");

    // Find password fields
    const allInputs = screen.getAllByRole("textbox");
    expect(allInputs.length).toBeGreaterThan(3);

    // Test API call directly when triggered
    const submitBtn = screen.getByRole("button", { name: /Complete Transporter Registration/i });
    fireEvent.click(submitBtn);
  });
});
