import React from "react";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { ToastProvider, useToast } from "./index";

const TestToastTrigger: React.FC = () => {
  const { success, error, warning, info, clearToasts } = useToast();

  return (
    <div>
      <button type="button" onClick={() => success("Profile saved successfully", "Success")}>
        Trigger Success
      </button>
      <button type="button" onClick={() => error("Network request failed", "Error")}>
        Trigger Error
      </button>
      <button type="button" onClick={() => warning("Account requires verification", "Warning")}>
        Trigger Warning
      </button>
      <button type="button" onClick={() => info("System maintenance at midnight", "Info")}>
        Trigger Info
      </button>
      <button type="button" onClick={clearToasts}>
        Clear All
      </button>
    </div>
  );
};

describe("Toast and Alert System", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  it("throws error when useToast is used outside of ToastProvider", () => {
    // Suppress React boundary console.error for expected throw
    const originalConsoleError = console.error;
    console.error = vi.fn();

    const InvalidConsumer = () => {
      useToast();
      return <div>Will not render</div>;
    };

    expect(() => render(<InvalidConsumer />)).toThrow(
      "useToast must be used within a ToastProvider"
    );

    console.error = originalConsoleError;
  });

  it("renders success toast with role status and title", () => {
    render(
      <ToastProvider>
        <TestToastTrigger />
      </ToastProvider>
    );

    act(() => {
      fireEvent.click(screen.getByRole("button", { name: "Trigger Success" }));
    });

    const toastElement = screen.getByRole("status");
    expect(toastElement).toBeInTheDocument();
    expect(screen.getByText("Success")).toBeInTheDocument();
    expect(screen.getByText("Profile saved successfully")).toBeInTheDocument();
  });

  it("renders error toast with role alert and assertive announcement", () => {
    render(
      <ToastProvider>
        <TestToastTrigger />
      </ToastProvider>
    );

    act(() => {
      fireEvent.click(screen.getByRole("button", { name: "Trigger Error" }));
    });

    const alertElement = screen.getByRole("alert");
    expect(alertElement).toBeInTheDocument();
    expect(alertElement).toHaveAttribute("aria-live", "assertive");
    expect(screen.getByText("Error")).toBeInTheDocument();
    expect(screen.getByText("Network request failed")).toBeInTheDocument();
  });

  it("renders warning toast with role alert", () => {
    render(
      <ToastProvider>
        <TestToastTrigger />
      </ToastProvider>
    );

    act(() => {
      fireEvent.click(screen.getByRole("button", { name: "Trigger Warning" }));
    });

    const alertElement = screen.getByRole("alert");
    expect(alertElement).toBeInTheDocument();
    expect(screen.getByText("Warning")).toBeInTheDocument();
    expect(screen.getByText("Account requires verification")).toBeInTheDocument();
  });

  it("renders info toast with role status and polite announcement", () => {
    render(
      <ToastProvider>
        <TestToastTrigger />
      </ToastProvider>
    );

    act(() => {
      fireEvent.click(screen.getByRole("button", { name: "Trigger Info" }));
    });

    const statusElement = screen.getByRole("status");
    expect(statusElement).toBeInTheDocument();
    expect(statusElement).toHaveAttribute("aria-live", "polite");
    expect(screen.getByText("Info")).toBeInTheDocument();
    expect(screen.getByText("System maintenance at midnight")).toBeInTheDocument();
  });

  it("automatically dismisses toast after default duration", () => {
    render(
      <ToastProvider defaultDuration={3000}>
        <TestToastTrigger />
      </ToastProvider>
    );

    act(() => {
      fireEvent.click(screen.getByRole("button", { name: "Trigger Success" }));
    });
    expect(screen.getByText("Profile saved successfully")).toBeInTheDocument();

    // Fast-forward 3000ms
    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(screen.queryByText("Profile saved successfully")).not.toBeInTheDocument();
  });

  it("allows manual dismissal via close button before timeout", () => {
    render(
      <ToastProvider defaultDuration={10000}>
        <TestToastTrigger />
      </ToastProvider>
    );

    act(() => {
      fireEvent.click(screen.getByRole("button", { name: "Trigger Success" }));
    });
    expect(screen.getByText("Profile saved successfully")).toBeInTheDocument();

    const dismissButton = screen.getByRole("button", { name: "Dismiss notification" });
    act(() => {
      fireEvent.click(dismissButton);
    });

    expect(screen.queryByText("Profile saved successfully")).not.toBeInTheDocument();
  });

  it("supports clearing all active toasts simultaneously", () => {
    render(
      <ToastProvider defaultDuration={10000}>
        <TestToastTrigger />
      </ToastProvider>
    );

    act(() => {
      fireEvent.click(screen.getByRole("button", { name: "Trigger Success" }));
      fireEvent.click(screen.getByRole("button", { name: "Trigger Error" }));
    });

    expect(screen.getByText("Profile saved successfully")).toBeInTheDocument();
    expect(screen.getByText("Network request failed")).toBeInTheDocument();

    act(() => {
      fireEvent.click(screen.getByRole("button", { name: "Clear All" }));
    });

    expect(screen.queryByText("Profile saved successfully")).not.toBeInTheDocument();
    expect(screen.queryByText("Network request failed")).not.toBeInTheDocument();
  });

  it("enforces maxToasts limit by discarding oldest toasts", () => {
    render(
      <ToastProvider maxToasts={2} defaultDuration={10000}>
        <TestToastTrigger />
      </ToastProvider>
    );

    act(() => {
      fireEvent.click(screen.getByRole("button", { name: "Trigger Success" }));
      fireEvent.click(screen.getByRole("button", { name: "Trigger Error" }));
      fireEvent.click(screen.getByRole("button", { name: "Trigger Warning" }));
    });

    // Only 2 most recent should be in DOM (Error and Warning, Success discarded)
    expect(screen.queryByText("Profile saved successfully")).not.toBeInTheDocument();
    expect(screen.getByText("Network request failed")).toBeInTheDocument();
    expect(screen.getByText("Account requires verification")).toBeInTheDocument();
  });

  it("prevents rapid identical toast flooding through deduplication", () => {
    render(
      <ToastProvider defaultDuration={10000}>
        <TestToastTrigger />
      </ToastProvider>
    );

    // Rapid double click
    act(() => {
      fireEvent.click(screen.getByRole("button", { name: "Trigger Success" }));
      fireEvent.click(screen.getByRole("button", { name: "Trigger Success" }));
    });

    // Only one toast item should be rendered
    const toastItems = screen.getAllByText("Profile saved successfully");
    expect(toastItems.length).toBe(1);
  });
});
