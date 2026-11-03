import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { OrdersPage } from "./OrdersPage";
import { ordersApi } from "../api/orders";
import { authStore } from "../store/authStore";
import type { OrderListItem, OrderListResponse, OrderDetail } from "../types/orders";
import type { User } from "../types";

describe("OrdersPage", () => {
  const mockUser: User = {
    id: "user-farmer-1",
    email: "ramesh@farm.com",
    role: "farmer",
    verification_status: "verified",
    account_status: "active",
    created_at: "2026-11-01T00:00:00Z",
    updated_at: "2026-11-01T00:00:00Z",
  };

  const mockOrders: OrderListItem[] = [
    {
      id: "order-001",
      order_number: "ORD-2026-0001",
      source_offer_id: "off-1",
      buyer_id: "user-buyer-1",
      farmer_id: "user-farmer-1",
      total_amount: 45000,
      currency: "INR",
      status: "pending",
      delivery_status: "not_arranged",
      delivery_arranged_date: null,
      items_count: 3,
      created_at: "2026-11-02T10:00:00Z",
      updated_at: "2026-11-02T10:00:00Z",
    },
  ];

  const mockListResponse: OrderListResponse = {
    items: mockOrders,
    total: 1,
    page: 1,
    page_size: 10,
    total_pages: 1,
  };

  const mockOrderDetail: OrderDetail = {
    ...mockOrders[0],
    delivery_method: "ex_farm",
    delivery_destination_address: null,
    delivery_notes: "Payment upon farm gate load inspection",
    cancellation_reason: null,
    cancelled_by_user_id: null,
    cancelled_at: null,
    completed_at: null,
    items: [
      {
        id: "item-1",
        order_id: "order-001",
        listing_id: "list-1",
        buyer_requirement_id: null,
        product_name: "Fresh Red Onions",
        quantity: 1500,
        unit: "kg",
        unit_price: 30,
        subtotal: 45000,
        quality_grade: "Grade A",
        status: "confirmed",
        created_at: "2026-11-02T10:00:00Z",
      },
    ],
    buyer: {
      id: "user-buyer-1",
      full_name: "Priya Sharma",
      email: "priya@agrocorp.com",
      business_name: "AgroCorp Processing Ltd",
    },
    farmer: {
      id: "user-farmer-1",
      full_name: "Ramesh Patel",
      email: "ramesh@farm.com",
      farm_name: "Patel Organic Farms",
    },
    amendments: [],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    authStore.reset();
    authStore.setUser(mockUser);
  });

  it("renders page title, status tabs and orders table", async () => {
    vi.spyOn(ordersApi, "listOrders").mockResolvedValue(mockListResponse);

    render(
      <MemoryRouter>
        <OrdersPage />
      </MemoryRouter>
    );

    expect(screen.getByText(/Commercial Orders Ledger/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /All Orders/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Confirmed$/i })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getAllByText("ORD-2026-0001").length).toBeGreaterThan(0);
    });

    const rows = screen.getAllByRole("row");
    const dataRow = rows.find((r) => within(r).queryByText("ORD-2026-0001"));
    expect(dataRow).toBeDefined();
    if (dataRow) {
      expect(within(dataRow).getByText(/₹45,000/i)).toBeInTheDocument();
      expect(within(dataRow).getByText(/Commercial Buyer/i)).toBeInTheDocument();
    }
  });

  it("filters orders by status filter button", async () => {
    vi.spyOn(ordersApi, "listOrders").mockResolvedValue(mockListResponse);

    render(
      <MemoryRouter>
        <OrdersPage />
      </MemoryRouter>
    );

    const confirmedTab = screen.getByRole("button", { name: /^Confirmed$/i });
    fireEvent.click(confirmedTab);

    await waitFor(() => {
      expect(ordersApi.listOrders).toHaveBeenCalledWith(
        expect.objectContaining({ status: "confirmed" })
      );
    });
  });

  it("opens order detail modal when clicking View Order", async () => {
    vi.spyOn(ordersApi, "listOrders").mockResolvedValue(mockListResponse);
    vi.spyOn(ordersApi, "getOrderDetail").mockResolvedValue(mockOrderDetail);
    vi.spyOn(ordersApi, "listAmendments").mockResolvedValue({ items: [], total: 0 });

    render(
      <MemoryRouter>
        <OrdersPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getAllByText("ORD-2026-0001").length).toBeGreaterThan(0);
    });

    const viewButtons = screen.getAllByRole("button", { name: /View Order/i });
    fireEvent.click(viewButtons[0]);

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(screen.getByText("Fresh Red Onions")).toBeInTheDocument();
      expect(screen.getByText(/Confirm Order/i)).toBeInTheDocument();
    });
  });
});
