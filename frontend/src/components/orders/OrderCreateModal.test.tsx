import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { OrderCreateModal } from "./OrderCreateModal";
import { ordersApi } from "../../api/orders";
import type { ProduceListingDetail } from "../../types/listings";
import type { OrderDetail } from "../../types/orders";

const mockUser = {
  id: "buyer-uuid-1",
  email: "buyer@test.com",
  role: "buyer",
  verification_status: "verified",
  buyer_profile: {
    business_name: "Buyer Co",
    delivery_receiving_address: "123 Market St, Pune",
  },
};

vi.mock("../../store/authStore", () => ({
  useAuth: () => ({
    user: mockUser,
  }),
}));

const mockListing: ProduceListingDetail = {
  id: "listing-uuid-100",
  farmer_id: "farmer-uuid-200",
  title: "Organic Fresh Tomatoes",
  product_name: "Tomatoes",
  initial_quantity: 500,
  available_quantity: 500,
  unit: "kg",
  price_per_unit: 40,
  quality_grade: "Grade A",
  location_city: "Nashik",
  location_state: "Maharashtra",
  status: "active",
  is_deleted: false,
  images: [],
  available_from: "2099-11-24",
  expires_at: "2099-12-24T00:00:00Z",
  created_at: "2026-11-24T00:00:00Z",
  updated_at: "2026-11-24T00:00:00Z",
};

const mockCreatedOrder: OrderDetail = {
  id: "order-uuid-999",
  order_number: "ORD-20261124-ABCDE",
  buyer_id: "buyer-uuid-1",
  farmer_id: "farmer-uuid-200",
  total_amount: 4000,
  currency: "INR",
  status: "pending",
  delivery_status: "not_arranged",
  created_at: "2026-11-24T10:00:00Z",
  updated_at: "2026-11-24T10:00:00Z",
  items: [
    {
      id: "item-1",
      order_id: "order-uuid-999",
      product_name: "Tomatoes",
      quantity: 100,
      unit: "kg",
      unit_price: 40,
      subtotal: 4000,
      status: "confirmed",
      created_at: "2026-11-24T10:00:00Z",
    },
  ],
  amendments: [],
};

describe("OrderCreateModal", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders listing rate, available volume, and product title", () => {
    render(
      <OrderCreateModal
        isOpen={true}
        listing={mockListing}
        onClose={vi.fn()}
        onSuccess={vi.fn()}
      />
    );

    expect(screen.getByText("Tomatoes")).toBeInTheDocument();
    expect(screen.getByText("Organic Fresh Tomatoes")).toBeInTheDocument();
    expect(screen.getByLabelText(/Order Volume/i)).toBeInTheDocument();
  });

  it("submits order with quantity and calls ordersApi.createOrder", async () => {
    const createSpy = vi.spyOn(ordersApi, "createOrder").mockResolvedValue(mockCreatedOrder);
    const handleSuccess = vi.fn();
    const handleClose = vi.fn();

    render(
      <OrderCreateModal
        isOpen={true}
        listing={mockListing}
        onClose={handleClose}
        onSuccess={handleSuccess}
      />
    );

    const submitBtn = screen.getByRole("button", { name: /Confirm & Place Order/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledTimes(1);
      expect(handleSuccess).toHaveBeenCalledWith(mockCreatedOrder);
      expect(handleClose).toHaveBeenCalled();
    });
  });

  it("synchronous click lock prevents duplicate submissions on rapid double clicks", async () => {
    let resolveOrder!: (val: OrderDetail) => void;
    const pendingPromise = new Promise<OrderDetail>((resolve) => {
      resolveOrder = resolve;
    });

    const createSpy = vi.spyOn(ordersApi, "createOrder").mockImplementation(() => pendingPromise);
    const handleSuccess = vi.fn();
    const handleClose = vi.fn();

    render(
      <OrderCreateModal
        isOpen={true}
        listing={mockListing}
        onClose={handleClose}
        onSuccess={handleSuccess}
      />
    );

    const submitBtn = screen.getByRole("button", { name: /Confirm & Place Order/i });

    // Rapid double click
    fireEvent.click(submitBtn);
    fireEvent.click(submitBtn);

    expect(createSpy).toHaveBeenCalledTimes(1);

    // Resolve promise and wait for completion to settle
    resolveOrder(mockCreatedOrder);
    await waitFor(() => {
      expect(handleSuccess).toHaveBeenCalledWith(mockCreatedOrder);
      expect(handleClose).toHaveBeenCalled();
    });
  });
});
