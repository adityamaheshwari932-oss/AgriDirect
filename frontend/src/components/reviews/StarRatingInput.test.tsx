import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StarRatingInput } from "./StarRatingInput";

describe("StarRatingInput", () => {
  it("renders with label and 5 stars", () => {
    const handleChange = vi.fn();
    render(<StarRatingInput value={3} onChange={handleChange} label="Produce Quality" required />);

    expect(screen.getByText("Produce Quality")).toBeInTheDocument();
    expect(screen.getByText("3/5")).toBeInTheDocument();

    const buttons = screen.getAllByRole("radio");
    expect(buttons).toHaveLength(5);
  });

  it("calls onChange when a star is clicked", () => {
    const handleChange = vi.fn();
    render(<StarRatingInput value={2} onChange={handleChange} />);

    const buttons = screen.getAllByRole("radio");
    fireEvent.click(buttons[3]); // 4th star

    expect(handleChange).toHaveBeenCalledWith(4);
  });
});

