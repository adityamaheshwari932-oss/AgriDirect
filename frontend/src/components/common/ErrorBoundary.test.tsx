import React, { useState } from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { ErrorBoundary } from "./ErrorBoundary";

const ThrowError: React.FC<{ shouldThrow?: boolean; message?: string }> = ({
  shouldThrow = true,
  message = "Boom! Rendering crashed",
}) => {
  if (shouldThrow) {
    throw new Error(message);
  }
  return <div>Normal Content Loaded</div>;
};

describe("ErrorBoundary Component", () => {
  // Suppress console.error during expected throw tests
  const originalError = console.error;
  beforeEach(() => {
    console.error = vi.fn();
  });

  afterEach(() => {
    console.error = originalError;
  });

  it("renders children normally when no error occurs", () => {
    render(
      <ErrorBoundary>
        <div>Safe Child Content</div>
      </ErrorBoundary>
    );

    expect(screen.getByText("Safe Child Content")).toBeInTheDocument();
  });

  it("catches descendant rendering error and displays fallback UI", () => {
    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(
      screen.getByText(/an unexpected technical error prevented this section/i)
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });

  it("calls onError callback when an unhandled error is caught", () => {
    const onErrorMock = vi.fn();

    render(
      <ErrorBoundary onError={onErrorMock}>
        <ThrowError message="Custom error for callback" />
      </ErrorBoundary>
    );

    expect(onErrorMock).toHaveBeenCalledTimes(1);
    expect(onErrorMock).toHaveBeenCalledWith(
      expect.objectContaining({ message: "Custom error for callback" }),
      expect.objectContaining({ componentStack: expect.any(String) })
    );
  });

  it("recovers and renders normal children after Try Again action is clicked", () => {
    const ParentComponent: React.FC = () => {
      const [hasError, setHasError] = useState(true);

      return (
        <div>
          <button type="button" onClick={() => setHasError(false)}>
            Fix Component
          </button>
          <ErrorBoundary onReset={() => setHasError(false)}>
            <ThrowError shouldThrow={hasError} message="Temporary crash" />
          </ErrorBoundary>
        </div>
      );
    };

    render(<ParentComponent />);

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();

    // Click "Try Again" which triggers onReset and resets boundary state
    const tryAgainBtn = screen.getByRole("button", { name: /try again/i });
    fireEvent.click(tryAgainBtn);

    expect(screen.getByText("Normal Content Loaded")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("renders a custom ReactNode fallback when provided", () => {
    render(
      <ErrorBoundary fallback={<div data-testid="custom-fallback">Custom Error Screen</div>}>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByTestId("custom-fallback")).toBeInTheDocument();
    expect(screen.getByText("Custom Error Screen")).toBeInTheDocument();
  });

  it("renders a custom functional fallback with error and reset handler", () => {
    const customFallbackFn = vi.fn((err: Error, reset: () => void) => (
      <div>
        <span>Handled error: {err.message}</span>
        <button type="button" onClick={reset}>
          Custom Reset
        </button>
      </div>
    ));

    render(
      <ErrorBoundary fallback={customFallbackFn}>
        <ThrowError message="Custom functional error" />
      </ErrorBoundary>
    );

    expect(customFallbackFn).toHaveBeenCalled();
    expect(screen.getByText("Handled error: Custom functional error")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Custom Reset" })).toBeInTheDocument();
  });
});

