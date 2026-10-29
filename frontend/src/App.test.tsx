import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "./App";

describe("App smoke test", () => {
  it("renders the AgriDirect platform title and tagline", () => {
    render(<App />);

    expect(screen.getAllByText("AgriDirect")[0]).toBeInTheDocument();
    expect(
      screen.getByText("Agricultural Marketplace")
    ).toBeInTheDocument();
  });

  it("renders the primary mission headline", () => {
    render(<App />);

    expect(
      screen.getByText("Connecting Farmers Directly with Commercial Buyers")
    ).toBeInTheDocument();
  });

  it("renders the core marketplace pillars", () => {
    render(<App />);

    expect(screen.getByText("Verified Farmers")).toBeInTheDocument();
    expect(screen.getByText("Commercial Buyers")).toBeInTheDocument();
    expect(screen.getByText("Structured Trade")).toBeInTheDocument();
  });

  it("renders the platform compliance disclaimer", () => {
    render(<App />);

    expect(
      screen.getByText(/AgriDirect facilitates direct commercial trade/i)
    ).toBeInTheDocument();
  });
});
