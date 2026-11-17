import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { LoadingState, EmptyState, ErrorState, ForbiddenState } from "./index";

describe("Consistent Application State Components", () => {
  describe("LoadingState", () => {
    it("renders default message and accessible status role", () => {
      render(<LoadingState />);

      expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
      expect(screen.getByText("Loading...")).toBeInTheDocument();
    });

    it("renders custom message and subtext", () => {
      render(
        <LoadingState
          message="Fetching produce listings..."
          subtext="Connecting to regional farm databases"
        />
      );

      expect(screen.getByText("Fetching produce listings...")).toBeInTheDocument();
      expect(
        screen.getByText("Connecting to regional farm databases")
      ).toBeInTheDocument();
    });
  });

  describe("EmptyState", () => {
    it("renders title, description, and action button", () => {
      const handleAction = vi.fn();
      render(
        <EmptyState
          title="No Produce Listings Found"
          description="You haven't listed any farm crops for sale yet."
          actionLabel="Create First Listing"
          onAction={handleAction}
        />
      );

      expect(screen.getByText("No Produce Listings Found")).toBeInTheDocument();
      expect(
        screen.getByText("You haven't listed any farm crops for sale yet.")
      ).toBeInTheDocument();

      const actionBtn = screen.getByRole("button", { name: "Create First Listing" });
      fireEvent.click(actionBtn);

      expect(handleAction).toHaveBeenCalledTimes(1);
    });

    it("renders default localized title when no title is provided", () => {
      render(<EmptyState />);
      expect(screen.getByText("No results found")).toBeInTheDocument();
    });
  });

  describe("ErrorState", () => {
    it("renders error alert with title, message, and retry button", () => {
      const handleRetry = vi.fn();
      render(
        <ErrorState
          title="Market Data Offline"
          message="Unable to calculate volume-weighted average price."
          onRetry={handleRetry}
        />
      );

      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.getByText("Market Data Offline")).toBeInTheDocument();
      expect(
        screen.getByText("Unable to calculate volume-weighted average price.")
      ).toBeInTheDocument();

      const retryBtn = screen.getByRole("button", { name: /try again/i });
      fireEvent.click(retryBtn);

      expect(handleRetry).toHaveBeenCalledTimes(1);
    });
  });

  describe("ForbiddenState", () => {
    it("renders forbidden alert with title, description, and return link", () => {
      render(
        <MemoryRouter>
          <ForbiddenState
            title="Permission Denied"
            message="Your account is restricted from posting fulfillment offers."
            returnTo="/dashboard/buyer"
            returnLabel="Back to Procurement"
          />
        </MemoryRouter>
      );

      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.getByText("Permission Denied")).toBeInTheDocument();
      expect(
        screen.getByText("Your account is restricted from posting fulfillment offers.")
      ).toBeInTheDocument();

      const returnLink = screen.getByRole("link", { name: /back to procurement/i });
      expect(returnLink).toHaveAttribute("href", "/dashboard/buyer");
    });
  });
});

