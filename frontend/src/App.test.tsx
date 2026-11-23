import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "./App";

describe("App smoke test", () => {
  it("renders the AgriDirect platform title and tagline", async () => {
    render(<App />);

    const brandTitles = await screen.findAllByText("AgriDirect");
    expect(brandTitles[0]).toBeInTheDocument();
    expect(
      await screen.findByText("Agricultural Marketplace")
    ).toBeInTheDocument();
  });

  it("renders the primary mission headline", async () => {
    render(<App />);

    expect(
      await screen.findByText("Connecting Farmers Directly with Commercial Buyers")
    ).toBeInTheDocument();
  });

  it("renders the core marketplace pillars", async () => {
    render(<App />);

    expect(await screen.findByText("Verified Farmers")).toBeInTheDocument();
    expect(await screen.findByText("Commercial Buyers")).toBeInTheDocument();
    expect(await screen.findByText("Structured Trade")).toBeInTheDocument();
  });

  it("renders the platform compliance disclaimer", async () => {
    render(<App />);

    expect(
      await screen.findByText(/AgriDirect facilitates direct commercial trade/i)
    ).toBeInTheDocument();
  });
});
