import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { OrderSlipModal } from "./OrderSlipModal";
import type { OrderDetail } from "../../types/orders";
import type { PaymentSummary } from "../../types/payments";

describe("OrderSlipModal", () => {
  const mockOrder: OrderDetail = {
    id: "order-test-uuid-123",
    order_number: "ORD-2026-9999",
    source_offer_id: "off-1",
    buyer_id: "buyer-1",
    farmer_id: "farmer-1",
    total_amount: 150000,
    currency: "INR",
    status: "completed",
    delivery_status: "completed",
    delivery_method: "direct_road_transit",
    delivery_destination_address: "Agro Foods Silo #4, Nashik, Maharashtra",
    delivery_arranged_date: "2026-04-10",
    delivery_acknowledged_at: "2026-04-12T14:30:00Z",
    completed_at: "2026-04-12T15:00:00Z",
    delivery_notes: "Inspected at warehouse dock",
    delivery_completion_marked_by_user_id: "farmer-1",
    delivery_completion_marked_at: "2026-04-12T12:00:00Z",
    delivery_acknowledged_by_user_id: "buyer-1",
    created_at: "2026-04-01T10:00:00Z",
    updated_at: "2026-04-12T15:00:00Z",
    items: [
      {
        id: "item-1",
        order_id: "order-test-uuid-123",
        product_name: "Grade A Alphonso Mangoes",
        quantity: 500,
        unit: "crates",
        unit_price: 300,
        subtotal: 150000,
        quality_grade: "Grade A Export",
        status: "fulfilled",
        created_at: "2026-04-01T10:00:00Z",
      },
    ],
    buyer: {
      id: "buyer-1",
      full_name: "Rajesh Sharma",
      email: "buyer@freshretail.com",
      phone: "+91 98765 43210",
      business_name: "Fresh Retail Supermarkets Ltd",
    },
    farmer: {
      id: "farmer-1",
      full_name: "Ramesh Patil",
      email: "ramesh@ratnagiriagro.com",
      phone: "+91 91234 56789",
      farm_name: "Ratnagiri Organic Orchards",
    },
    amendments: [],
  };

  const mockPaymentSummary: PaymentSummary = {
    order_id: "order-test-uuid-123",
    order_total: "150000",
    total_recorded: "150000",
    total_acknowledged: "150000",
    total_disputed: "0",
    unacknowledged_amount: "0",
    remaining_acknowledged_balance: "0",
    remaining_payable_amount: "0",
    max_available_for_new_payment: "0",
    settlement_status: "fully_settled",
    records_count: 1,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does not render when isOpen is false", () => {
    const { container } = render(
      <OrderSlipModal
        isOpen={false}
        order={mockOrder}
        onClose={vi.fn()}
      />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders order slip modal with full B2B particulars when open", () => {
    render(
      <OrderSlipModal
        isOpen={true}
        order={mockOrder}
        paymentSummary={mockPaymentSummary}
        onClose={vi.fn()}
      />
    );

    // Title & Slip reference
    expect(screen.getByText(/Trade Confirmation & Delivery Slip/i)).toBeInTheDocument();
    expect(screen.getByText(/SLIP-ORD-2026-9999/i)).toBeInTheDocument();

    // Farmer particulars
    expect(screen.getAllByText("Ratnagiri Organic Orchards").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Contact: Ramesh Patil/i)).toBeInTheDocument();
    expect(screen.getByText("ramesh@ratnagiriagro.com")).toBeInTheDocument();

    // Buyer particulars
    expect(screen.getAllByText("Fresh Retail Supermarkets Ltd").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Authorized Rep: Rajesh Sharma/i)).toBeInTheDocument();
    expect(screen.getByText("buyer@freshretail.com")).toBeInTheDocument();
    expect(screen.getByText(/Destination: Agro Foods Silo #4, Nashik, Maharashtra/i)).toBeInTheDocument();

    // Commodity manifest
    expect(screen.getByText("Grade A Alphonso Mangoes")).toBeInTheDocument();
    expect(screen.getByText("Grade A Export")).toBeInTheDocument();
    expect(screen.getByText("500 crates")).toBeInTheDocument();

    // Financial ledger
    expect(screen.getAllByText("₹1,50,000").length).toBeGreaterThanOrEqual(2);

    // Regulatory Notice
    expect(screen.getByText(/AgriDirect is an electronic marketplace facilitating direct commercial trade/i)).toBeInTheDocument();
  });

  it("calls window.print when Print / Save as PDF button is clicked", () => {
    const printSpy = vi.spyOn(window, "print").mockImplementation(() => {});

    render(
      <OrderSlipModal
        isOpen={true}
        order={mockOrder}
        onClose={vi.fn()}
      />
    );

    const printButton = screen.getByRole("button", { name: /Print \/ Save as PDF/i });
    fireEvent.click(printButton);

    expect(printSpy).toHaveBeenCalledTimes(1);
    printSpy.mockRestore();
  });

  it("calls onClose when close button is clicked", () => {
    const onCloseMock = vi.fn();

    render(
      <OrderSlipModal
        isOpen={true}
        order={mockOrder}
        onClose={onCloseMock}
      />
    );

    const closeButton = screen.getByRole("button", { name: /Close dialog/i });
    fireEvent.click(closeButton);

    expect(onCloseMock).toHaveBeenCalledTimes(1);
  });
});
