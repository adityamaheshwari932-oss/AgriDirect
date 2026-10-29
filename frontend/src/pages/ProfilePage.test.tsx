import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProfilePage } from "./ProfilePage";
import { authStore } from "../store/authStore";
import { usersApi } from "../api/users";
import { ApiError } from "../api/errors";
import { InMemoryTokenStorage, tokenStorage } from "../api/tokenStorage";
import type { User } from "../types";

describe("ProfilePage", () => {
  const mockFarmerUser: User = {
    id: "farmer-id-12345",
    email: "farmer@valleyfarms.test",
    phone_number: "+91 98765 43210",
    role: "farmer",
    verification_status: "verified",
    account_status: "active",
    created_at: "2026-10-29T10:00:00Z",
    updated_at: "2026-10-29T10:00:00Z",
    farmer_profile: {
      id: "f-prof-123",
      full_name: "Ramesh Patel",
      farm_name: "Patel Organic Farms",
      farm_location_address: "Survey No. 42, Dindori Road",
      city: "Nashik",
      state: "Maharashtra",
      postal_code: "422004",
      farm_size_acres: 18.5,
      farming_practices: "organic",
      primary_crops: "Grapes, Pomegranates, Onions",
      bio: "Eco-certified organic orchard operation.",
      created_at: "2026-10-29T10:00:00Z",
      updated_at: "2026-10-29T10:00:00Z",
    },
  };

  const mockBuyerUser: User = {
    id: "buyer-id-67890",
    email: "procurement@tajdining.test",
    phone_number: "+91 22 9876 5432",
    role: "buyer",
    verification_status: "pending",
    account_status: "active",
    created_at: "2026-10-29T10:00:00Z",
    updated_at: "2026-10-29T10:00:00Z",
    buyer_profile: {
      id: "b-prof-456",
      contact_person_name: "Pooja Mehta",
      business_name: "Taj Dining Enterprises",
      business_type: "restaurant",
      business_registration_number: "27AABCT1234F1Z1",
      delivery_receiving_address: "Central Receiving Dock, Kitchen Facility 2",
      city: "Mumbai",
      state: "Maharashtra",
      postal_code: "400001",
      procurement_summary: "High volume daily organic farm vegetables.",
      bio: "Premium hospitality and farm-to-table dining chain.",
      created_at: "2026-10-29T10:00:00Z",
      updated_at: "2026-10-29T10:00:00Z",
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
        <ProfilePage />
      </MemoryRouter>
    );
  };

  it("renders protected server-controlled attributes in View Mode without editable inputs", () => {
    authStore["state"] = {
      status: "authenticated",
      user: mockFarmerUser,
      error: null,
    };

    renderComponent();

    // Check header
    expect(screen.getByRole("heading", { name: /account & commercial profile/i })).toBeInTheDocument();

    // Check server-managed attributes
    expect(screen.getByText("farmer-id-12345")).toBeInTheDocument();
    expect(screen.getByText("farmer@valleyfarms.test")).toBeInTheDocument();
    expect(screen.getByText("Agricultural Producer")).toBeInTheDocument();
    expect(screen.getByText("Verified")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();

    // Email and User ID are NOT input elements in View Mode
    expect(screen.queryByLabelText(/registered email/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/account id/i)).not.toBeInTheDocument();
  });

  it("renders farmer view mode with current attributes and switches to edit mode", async () => {
    const user = userEvent.setup();
    authStore["state"] = {
      status: "authenticated",
      user: mockFarmerUser,
      error: null,
    };

    renderComponent();

    expect(screen.getByText("Ramesh Patel")).toBeInTheDocument();
    expect(screen.getByText("Patel Organic Farms")).toBeInTheDocument();
    expect(screen.getByText("18.5 Acres")).toBeInTheDocument();

    // Click Edit Profile
    const editBtn = screen.getByRole("button", { name: /edit profile/i });
    await user.click(editBtn);

    // Form inputs appear
    expect(screen.getByLabelText(/producer full name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/farm or enterprise name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/cultivated area \(acres\)/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /save changes/i })).toBeInTheDocument();
  });

  it("validates required farmer fields on submission in edit mode", async () => {
    const user = userEvent.setup();
    authStore["state"] = {
      status: "authenticated",
      user: mockFarmerUser,
      error: null,
    };

    renderComponent();

    await user.click(screen.getByRole("button", { name: /edit profile/i }));

    const nameInput = screen.getByLabelText(/producer full name/i);
    await user.clear(nameInput);

    await user.click(screen.getByRole("button", { name: /save changes/i }));

    expect(await screen.findByText(/full name is required/i)).toBeInTheDocument();
  });

  it("validates positive farm acreage in edit mode", async () => {
    const user = userEvent.setup();
    authStore["state"] = {
      status: "authenticated",
      user: mockFarmerUser,
      error: null,
    };

    renderComponent();

    await user.click(screen.getByRole("button", { name: /edit profile/i }));

    const acresInput = screen.getByLabelText(/cultivated area \(acres\)/i);
    await user.clear(acresInput);
    await user.type(acresInput, "-5");

    await user.click(screen.getByRole("button", { name: /save changes/i }));

    expect(
      await screen.findByText(/farm size must be a positive number of acres/i)
    ).toBeInTheDocument();
  });

  it("successfully updates farmer profile and returns to view mode with updated data", async () => {
    const user = userEvent.setup();
    authStore["state"] = {
      status: "authenticated",
      user: mockFarmerUser,
      error: null,
    };

    const updatedFarmer: User = {
      ...mockFarmerUser,
      farmer_profile: {
        ...mockFarmerUser.farmer_profile!,
        farm_name: "Patel Heritage Vineyards",
        farm_size_acres: 22,
      },
    };

    const updateSpy = vi
      .spyOn(usersApi, "updateFarmerProfile")
      .mockResolvedValueOnce(updatedFarmer);

    renderComponent();

    await user.click(screen.getByRole("button", { name: /edit profile/i }));

    const farmNameInput = screen.getByLabelText(/farm or enterprise name/i);
    await user.clear(farmNameInput);
    await user.type(farmNameInput, "Patel Heritage Vineyards");

    const acresInput = screen.getByLabelText(/cultivated area \(acres\)/i);
    await user.clear(acresInput);
    await user.type(acresInput, "22");

    await user.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          farm_name: "Patel Heritage Vineyards",
          farm_size_acres: 22,
        })
      );
    });

    // Check success notification and return to view mode
    expect(await screen.findByText(/farm profile updated successfully/i)).toBeInTheDocument();
    expect(screen.getByText("Patel Heritage Vineyards")).toBeInTheDocument();
  });

  it("handles duplicate phone number conflict (HTTP 409) in edit mode", async () => {
    const user = userEvent.setup();
    authStore["state"] = {
      status: "authenticated",
      user: mockFarmerUser,
      error: null,
    };

    vi.spyOn(usersApi, "updateFarmerProfile").mockRejectedValueOnce(
      new ApiError(409, "This phone number is already registered to another account.")
    );

    renderComponent();

    await user.click(screen.getByRole("button", { name: /edit profile/i }));

    const phoneInput = screen.getByLabelText(/contact phone number/i);
    await user.clear(phoneInput);
    await user.type(phoneInput, "+91 99999 88888");

    await user.click(screen.getByRole("button", { name: /save changes/i }));

    expect(
      await screen.findByText(/this phone number is already registered to another account/i)
    ).toBeInTheDocument();
    // Input value is preserved
    expect(phoneInput).toHaveValue("+91 99999 88888");
  });

  it("handles backend validation error (HTTP 422) and maps to form input", async () => {
    const user = userEvent.setup();
    authStore["state"] = {
      status: "authenticated",
      user: mockFarmerUser,
      error: null,
    };

    vi.spyOn(usersApi, "updateFarmerProfile").mockRejectedValueOnce(
      new ApiError(422, "Validation error", [
        { loc: ["body", "postal_code"], msg: "Invalid postal code format", type: "value_error" },
      ])
    );

    renderComponent();

    await user.click(screen.getByRole("button", { name: /edit profile/i }));

    await user.click(screen.getByRole("button", { name: /save changes/i }));

    expect(
      await screen.findByText(/validation error: please check highlighted fields/i)
    ).toBeInTheDocument();
  });

  it("cancels edits and restores previous values", async () => {
    const user = userEvent.setup();
    authStore["state"] = {
      status: "authenticated",
      user: mockFarmerUser,
      error: null,
    };

    renderComponent();

    await user.click(screen.getByRole("button", { name: /edit profile/i }));

    const nameInput = screen.getByLabelText(/producer full name/i);
    await user.clear(nameInput);
    await user.type(nameInput, "Changed Name Before Cancel");

    const cancelButtons = screen.getAllByRole("button", { name: /cancel/i });
    await user.click(cancelButtons[0]);

    // Back in view mode, previous name is intact
    expect(screen.getByText("Ramesh Patel")).toBeInTheDocument();
    expect(screen.queryByText("Changed Name Before Cancel")).not.toBeInTheDocument();
  });

  it("renders buyer profile and supports buyer profile updates", async () => {
    const user = userEvent.setup();
    authStore["state"] = {
      status: "authenticated",
      user: mockBuyerUser,
      error: null,
    };

    const updatedBuyer: User = {
      ...mockBuyerUser,
      buyer_profile: {
        ...mockBuyerUser.buyer_profile!,
        contact_person_name: "Pooja Mehta-Shah",
        business_type: "hotel",
      },
    };

    const updateSpy = vi
      .spyOn(usersApi, "updateBuyerProfile")
      .mockResolvedValueOnce(updatedBuyer);

    renderComponent();

    expect(screen.getByText("Pooja Mehta")).toBeInTheDocument();
    expect(screen.getByText("Taj Dining Enterprises")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /edit profile/i }));

    const contactInput = screen.getByLabelText(/contact person name/i);
    await user.clear(contactInput);
    await user.type(contactInput, "Pooja Mehta-Shah");

    await user.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          contact_person_name: "Pooja Mehta-Shah",
        })
      );
    });

    expect(
      await screen.findByText(/commercial business profile updated successfully/i)
    ).toBeInTheDocument();
  });
});
