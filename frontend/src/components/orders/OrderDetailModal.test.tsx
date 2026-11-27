import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { OrderDetailModal } from "./OrderDetailModal";
import { ordersApi } from "../../api/orders";
import { paymentsApi } from "../../api/payments";
import { authStore } from "../../store/authStore";
import type { OrderDetail } from "../../types/orders";
import type { User } from "../../types";

vi.mock("../../api/orders", () => ({
  ordersApi: {
    getOrderDetail: vi.fn(),
    listAmendments: vi.fn(),
    markDeliveryCompleted: vi.fn(),
    confirmOrder: vi.fn(),
    acceptAmendment: vi.fn(),
    rejectAmendment: vi.fn(),
  },
}));

vi.mock("../../api/payments", () => ({
  paymentsApi: {
    getOrderPaymentSummary: vi.fn(),
    listOrderPayments: vi.fn(),
  },
}));

describe("OrderDetailModal — Bilateral Delivery Acknowledgement", () => {
  const farmerUser: User = {
    id: "farmer-1",
    email: "farmer@test.com",
    role: "farmer",
    verification_status: "verified",
    account_status: "active",
    created_at: "2026-03-29T10:00:00Z",
    updated_at: "2026-03-29T10:00:00Z",
  };

  const buyerUser: User = {
    id: "buyer-1",
    email: "buyer@test.com",
    role: "buyer",
    verification_status: "verified",
    account_status: "active",
    created_at: "2026-03-29T10:00:00Z",
    updated_at: "2026-03-29T10:00:00Z",
  };

  const baseOrder: OrderDetail = {
    id: "order-123",
    order_number: "ORD-2026-0123",
    source_offer_id: "off-1",
    buyer_id: "buyer-1",
    farmer_id: "farmer-1",
    total_amount: 50000,
    currency: "INR",
    status: "delivery_arranged",
    delivery_status: "arranged",
    delivery_arranged_date: "2026-04-10",
    delivery_notes: "Express road transport",
    delivery_completion_marked_by_user_id: null,
    delivery_completion_marked_at: null,
    delivery_acknowledged_by_user_id: null,
    delivery_acknowledged_at: null,
    created_at: "2026-03-29T10:00:00Z",
    updated_at: "2026-03-29T10:00:00Z",
    items: [
      {
        id: "item-1",
        order_id: "order-123",
        product_name: "Grade A Wheat",
        quantity: 2000,
        unit: "kg",
        unit_price: 25,
        subtotal: 50000,
        status: "confirmed",
        created_at: "2026-03-29T10:00:00Z",
      },
    ],
    buyer: {
      id: "buyer-1",
      full_name: "Buyer Ramesh",
      email: "buyer@test.com",
      business_name: "Ramesh Agro Mills",
    },
    farmer: {
      id: "farmer-1",
      full_name: "Farmer Suresh",
      email: "farmer@test.com",
      farm_name: "Suresh Organic Farms",
    },
    amendments: [],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(paymentsApi.getOrderPaymentSummary).mockResolvedValue({
      order_id: "order-123",
      order_total: "50000",
      total_recorded: "0",
      total_acknowledged: "0",
      total_disputed: "0",
      unacknowledged_amount: "0",
      remaining_acknowledged_balance: "50000",
      remaining_payable_amount: "50000",
      max_available_for_new_payment: "50000",
      settlement_status: "unpaid",
      records_count: 0,
    });
    vi.mocked(ordersApi.listAmendments).mockResolvedValue({
      items: [],
      total: 0,
    });
  });

  it("does NOT show Acknowledge button when delivery_status is 'arranged' (prevents backend 409)", async () => {
    authStore.setUser(buyerUser);
    vi.mocked(ordersApi.getOrderDetail).mockResolvedValue(baseOrder);

    render(
      <MemoryRouter>
        <OrderDetailModal orderId="order-123" onClose={vi.fn()} />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/ORD-2026-0123/)).toBeInTheDocument();
    });

    // In 'arranged' status, only mark completed should be allowed, NEVER acknowledge
    expect(
      screen.queryByRole("button", { name: /Acknowledge Delivery Receipt/i })
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Mark Delivery Completed/i })
    ).toBeInTheDocument();
  });

  it("allows buyer to acknowledge when farmer marked completion, and prevents farmer self-acknowledgement", async () => {
    const farmerCompletedOrder: OrderDetail = {
      ...baseOrder,
      delivery_status: "completion_marked",
      delivery_completion_marked_by_user_id: "farmer-1",
      delivery_completion_marked_at: "2026-04-10T12:00:00Z",
    };

    // 1. Farmer viewing: should see awaiting message and NOT see Acknowledge button
    authStore.setUser(farmerUser);
    vi.mocked(ordersApi.getOrderDetail).mockResolvedValue(farmerCompletedOrder);

    const { unmount } = render(
      <MemoryRouter>
        <OrderDetailModal orderId="order-123" onClose={vi.fn()} />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Awaiting counterparty delivery receipt acknowledgement/i)).toBeInTheDocument();
    });
    expect(
      screen.queryByRole("button", { name: /Acknowledge Delivery Receipt/i })
    ).not.toBeInTheDocument();

    unmount();

    // 2. Buyer viewing: should see Acknowledge Delivery Receipt button
    authStore.setUser(buyerUser);
    render(
      <MemoryRouter>
        <OrderDetailModal orderId="order-123" onClose={vi.fn()} />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Acknowledge Delivery Receipt/i })
      ).toBeInTheDocument();
    });
    expect(
      screen.queryByText(/Awaiting counterparty delivery receipt acknowledgement/i)
    ).not.toBeInTheDocument();
  });

  it("allows farmer to acknowledge when buyer marked completion, and prevents buyer self-acknowledgement", async () => {
    const buyerCompletedOrder: OrderDetail = {
      ...baseOrder,
      delivery_status: "completion_marked",
      delivery_completion_marked_by_user_id: "buyer-1",
      delivery_completion_marked_at: "2026-04-10T14:00:00Z",
    };

    // 1. Buyer viewing: should see awaiting message and NOT see Acknowledge button
    authStore.setUser(buyerUser);
    vi.mocked(ordersApi.getOrderDetail).mockResolvedValue(buyerCompletedOrder);

    const { unmount } = render(
      <MemoryRouter>
        <OrderDetailModal orderId="order-123" onClose={vi.fn()} />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Awaiting counterparty delivery receipt acknowledgement/i)).toBeInTheDocument();
    });
    expect(
      screen.queryByRole("button", { name: /Acknowledge Delivery Receipt/i })
    ).not.toBeInTheDocument();

    unmount();

    // 2. Farmer viewing: should see Acknowledge Delivery Receipt button
    authStore.setUser(farmerUser);
    render(
      <MemoryRouter>
        <OrderDetailModal orderId="order-123" onClose={vi.fn()} />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Acknowledge Delivery Receipt/i })
      ).toBeInTheDocument();
    });
    expect(
      screen.queryByText(/Awaiting counterparty delivery receipt acknowledgement/i)
    ).not.toBeInTheDocument();
  });

  it("renders Trade Slip button for confirmed or completed order and opens slip modal on click", async () => {
    const completedOrder: OrderDetail = {
      ...baseOrder,
      status: "completed",
      delivery_status: "completed",
    };

    authStore.setUser(farmerUser);
    vi.mocked(ordersApi.getOrderDetail).mockResolvedValue(completedOrder);

    render(
      <MemoryRouter>
        <OrderDetailModal orderId="order-123" onClose={vi.fn()} />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/ORD-2026-0123/)).toBeInTheDocument();
    });

    // Check that Trade Slip button is present (in header or footer)
    const tradeSlipButtons = screen.getAllByRole("button", { name: /Trade Slip/i });
    expect(tradeSlipButtons.length).toBeGreaterThanOrEqual(1);

    // Click Trade Slip button
    fireEvent.click(tradeSlipButtons[0]);

    // Verify OrderSlipModal opened with document title
    expect(screen.getByText(/Trade Confirmation & Delivery Slip/i)).toBeInTheDocument();
    expect(screen.getByText(/SLIP-ORD-2026-0123/i)).toBeInTheDocument();
  });

  describe("D-2: Safe delivery_status access regression tests", () => {
    it("renders formatted delivery_status with underscores replaced by spaces", async () => {
      authStore.setUser(farmerUser);
      vi.mocked(ordersApi.getOrderDetail).mockResolvedValue({
        ...baseOrder,
        delivery_status: "not_arranged",
      });

      render(
        <MemoryRouter>
          <OrderDetailModal orderId="order-123" onClose={vi.fn()} />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/ORD-2026-0123/)).toBeInTheDocument();
      });

      const matched = screen.getAllByText("not arranged");
      expect(matched.length).toBeGreaterThanOrEqual(1);
    });

    it("renders safely without crashing when delivery_status is null", async () => {
      authStore.setUser(farmerUser);
      vi.mocked(ordersApi.getOrderDetail).mockResolvedValue({
        ...baseOrder,
        delivery_status: null as unknown as OrderDetail["delivery_status"],
      });

      render(
        <MemoryRouter>
          <OrderDetailModal orderId="order-123" onClose={vi.fn()} />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/ORD-2026-0123/)).toBeInTheDocument();
      });

      const unavailableLabels = screen.getAllByText(/Unavailable/i);
      expect(unavailableLabels.length).toBeGreaterThanOrEqual(1);
    });

    it("renders safely without crashing when delivery_status is undefined", async () => {
      authStore.setUser(farmerUser);
      const { delivery_status: _omittedDeliveryStatus, ...orderWithoutDeliveryStatus } =
        baseOrder;
      vi.mocked(ordersApi.getOrderDetail).mockResolvedValue(
        orderWithoutDeliveryStatus as unknown as OrderDetail
      );

      render(
        <MemoryRouter>
          <OrderDetailModal orderId="order-123" onClose={vi.fn()} />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/ORD-2026-0123/)).toBeInTheDocument();
      });

      const unavailableLabels = screen.getAllByText(/Unavailable/i);
      expect(unavailableLabels.length).toBeGreaterThanOrEqual(1);
    });

    it("renders safely without crashing when delivery_status is an unexpected non-string type", async () => {
      authStore.setUser(farmerUser);
      vi.mocked(ordersApi.getOrderDetail).mockResolvedValue({
        ...baseOrder,
        delivery_status: 12345 as unknown as OrderDetail["delivery_status"],
      });

      render(
        <MemoryRouter>
          <OrderDetailModal orderId="order-123" onClose={vi.fn()} />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/ORD-2026-0123/)).toBeInTheDocument();
      });

      const unavailableLabels = screen.getAllByText(/Unavailable/i);
      expect(unavailableLabels.length).toBeGreaterThanOrEqual(1);
    });
  });
});