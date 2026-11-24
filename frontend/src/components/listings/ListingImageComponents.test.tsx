import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { ListingCreateEditModal } from "./ListingCreateEditModal";
import { ListingImageModal } from "./ListingImageModal";
import { ProduceListingCard } from "../marketplace/ProduceListingCard";
import { ProduceDetailModal } from "../marketplace/ProduceDetailModal";
import { listingsApi } from "../../api/listings";
import type {
  ProduceCategory,
  ProduceListingDetail,
  ProduceListingPublicSummary,
} from "../../types/listings";

describe("Listing & Product Images Frontend Integration", () => {
  const mockCategories: ProduceCategory[] = [
    { id: "cat-1", name: "Grains & Cereals", slug: "grains", is_active: true },
  ];

  const mockListingWithImages: ProduceListingDetail = {
    id: "list-1",
    farmer_id: "farmer-1",
    category_id: "cat-1",
    product_name: "Sharbati Wheat",
    title: "Premium Sharbati Wheat Lot 1",
    initial_quantity: 100,
    available_quantity: 100,
    unit: "quintal",
    price_per_unit: 2500,
    location_state: "Madhya Pradesh",
    location_city: "Sehore",
    available_from: "2026-11-20",
    expires_at: "2026-12-20T00:00:00Z",
    status: "active",
    is_deleted: false,
    created_at: "2026-11-20T10:00:00Z",
    updated_at: "2026-11-20T10:00:00Z",
    images: [
      {
        id: "img-1",
        listing_id: "list-1",
        image_uri: "/uploads/products/list-1/img1.jpg",
        image_url: "/api/v1/listings/list-1/images/img-1",
        is_primary: true,
        display_order: 0,
        created_at: "2026-11-20T10:00:00Z",
      },
      {
        id: "img-2",
        listing_id: "list-1",
        image_uri: "/uploads/products/list-1/img2.jpg",
        image_url: "/api/v1/listings/list-1/images/img-2",
        is_primary: false,
        display_order: 1,
        created_at: "2026-11-20T10:01:00Z",
      },
    ],
  };

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe("ListingCreateEditModal Image Management", () => {
    it("renders image selection section with limits guidance", () => {
      render(
        <ListingCreateEditModal
          isOpen={true}
          categories={mockCategories}
          onClose={() => {}}
          onSuccess={() => {}}
        />
      );

      expect(screen.getByText(/Produce Lot Photographs/i)).toBeInTheDocument();
      expect(screen.getByText(/Max 10 photos, 5 MB each/i)).toBeInTheDocument();
      expect(screen.getByText(/Select or Take Harvest Photographs/i)).toBeInTheDocument();
    });

    it("rejects oversized images with error message", async () => {
      const { container } = render(
        <ListingCreateEditModal
          isOpen={true}
          categories={mockCategories}
          onClose={() => {}}
          onSuccess={() => {}}
        />
      );

      // Create a 6 MB dummy file
      const oversizedFile = new File([new ArrayBuffer(6 * 1024 * 1024)], "huge.jpg", {
        type: "image/jpeg",
      });

      const input = container.querySelector("#listing-images-input") as HTMLInputElement;
      fireEvent.change(input, { target: { files: [oversizedFile] } });

      expect(await screen.findByText(/exceeds the 5 MB limit/i)).toBeInTheDocument();
    });

    it("rejects unsupported file formats with error message", async () => {
      const { container } = render(
        <ListingCreateEditModal
          isOpen={true}
          categories={mockCategories}
          onClose={() => {}}
          onSuccess={() => {}}
        />
      );

      const invalidFile = new File(["dummy text"], "notes.txt", {
        type: "text/plain",
      });

      const input = container.querySelector("#listing-images-input") as HTMLInputElement;
      fireEvent.change(input, { target: { files: [invalidFile] } });

      expect(await screen.findByText(/unsupported.*format/i)).toBeInTheDocument();
    });

    it("displays existing images in edit mode with primary indicator", () => {
      render(
        <ListingCreateEditModal
          isOpen={true}
          listingToEdit={mockListingWithImages}
          categories={mockCategories}
          onClose={() => {}}
          onSuccess={() => {}}
        />
      );

      expect(screen.getByText(/Existing Photographs:/i)).toBeInTheDocument();
      expect(screen.getByText(/Primary/i)).toBeInTheDocument();
      expect(screen.getByTitle(/Make Primary Photo/i)).toBeInTheDocument();
      expect(screen.getAllByTitle(/Delete Photo/i)).toHaveLength(2);
    });

    it("uploads attached images after creating new listing", async () => {
      const onSuccessMock = vi.fn();
      const createdListing = { ...mockListingWithImages, images: [] };

      vi.spyOn(listingsApi, "createListing").mockResolvedValueOnce(createdListing);
      vi.spyOn(listingsApi, "uploadImages").mockResolvedValueOnce(mockListingWithImages.images);
      vi.spyOn(listingsApi, "getListing").mockResolvedValueOnce(mockListingWithImages);

      // Mock URL.createObjectURL
      global.URL.createObjectURL = vi.fn(() => "blob:http://localhost/test-preview");
      global.URL.revokeObjectURL = vi.fn();

      const { container } = render(
        <ListingCreateEditModal
          isOpen={true}
          categories={mockCategories}
          onClose={() => {}}
          onSuccess={onSuccessMock}
        />
      );

      fireEvent.change(screen.getByLabelText(/Produce Name/i), {
        target: { value: "Organic Rice" },
      });
      fireEvent.change(screen.getByLabelText(/Headline Title/i), {
        target: { value: "Fresh Basmati Rice Lot" },
      });
      fireEvent.change(screen.getByLabelText(/Total Supply Quantity/i), {
        target: { value: "50" },
      });
      fireEvent.change(screen.getByLabelText(/Price per Unit/i), {
        target: { value: "4500" },
      });

      const validFile = new File(["dummy png"], "crop.png", { type: "image/png" });
      const input = container.querySelector("#listing-images-input") as HTMLInputElement;
      fireEvent.change(input, { target: { files: [validFile] } });

      expect(screen.getByText("crop.png")).toBeInTheDocument();

      fireEvent.click(screen.getByRole("button", { name: /Publish Listing/i }));

      await waitFor(() => {
        expect(listingsApi.createListing).toHaveBeenCalled();
        expect(listingsApi.uploadImages).toHaveBeenCalledWith("list-1", [validFile]);
        expect(onSuccessMock).toHaveBeenCalledWith(mockListingWithImages, false);
      });
    });
  });

  describe("ProduceListingCard Thumbnail Display & Fallback", () => {
    it("renders image using primary_image_url when available", () => {
      const summaryWithImage: ProduceListingPublicSummary = {
        id: "list-1",
        product_name: "Sharbati Wheat",
        title: "Certified Organic Wheat",
        available_quantity: 50,
        unit: "quintal",
        price_per_unit: 2500,
        location_city: "Sehore",
        location_state: "Madhya Pradesh",
        available_from: "2026-11-20",
        expires_at: "2026-12-20",
        status: "active",
        created_at: "2026-11-20T10:00:00Z",
        primary_image_url: "/api/v1/listings/list-1/images/img-1",
      };

      render(
        <MemoryRouter>
          <ProduceListingCard listing={summaryWithImage} onViewDetails={() => {}} />
        </MemoryRouter>
      );

      const img = screen.getByRole("img") as HTMLImageElement;
      expect(img).toBeInTheDocument();
      expect(img.src).toContain("/api/v1/listings/list-1/images/img-1");
    });

    it("renders fallback placeholder when no image is present", () => {
      const summaryWithoutImage: ProduceListingPublicSummary = {
        id: "list-2",
        product_name: "Soybeans",
        title: "Standard Yellow Soybeans",
        available_quantity: 100,
        unit: "quintal",
        price_per_unit: 4200,
        location_city: "Indore",
        location_state: "Madhya Pradesh",
        available_from: "2026-11-20",
        expires_at: "2026-12-20",
        status: "active",
        created_at: "2026-11-20T10:00:00Z",
      };

      render(
        <MemoryRouter>
          <ProduceListingCard listing={summaryWithoutImage} onViewDetails={() => {}} />
        </MemoryRouter>
      );

      expect(screen.queryByRole("img")).not.toBeInTheDocument();
      expect(screen.getByText(/Farm Direct Lot/i)).toBeInTheDocument();
    });

    it("switches to tractor fallback when image fails to load (onError)", () => {
      const summaryBrokenImage: ProduceListingPublicSummary = {
        id: "list-3",
        product_name: "Mustard Seeds",
        title: "Yellow Mustard",
        available_quantity: 20,
        unit: "quintal",
        price_per_unit: 5000,
        location_city: "Bharatpur",
        location_state: "Rajasthan",
        available_from: "2026-11-20",
        expires_at: "2026-12-20",
        status: "active",
        created_at: "2026-11-20T10:00:00Z",
        primary_image_url: "/api/v1/listings/list-3/images/broken.jpg",
      };

      render(
        <MemoryRouter>
          <ProduceListingCard listing={summaryBrokenImage} onViewDetails={() => {}} />
        </MemoryRouter>
      );

      const img = screen.getByRole("img");
      fireEvent.error(img);

      expect(screen.getByText(/Farm Direct Lot/i)).toBeInTheDocument();
    });
  });

  describe("ProduceDetailModal Gallery Viewport & Fallback", () => {
    it("renders image gallery with active thumbnail ring", async () => {
      vi.spyOn(listingsApi, "getListing").mockResolvedValueOnce(mockListingWithImages);

      render(
        <MemoryRouter>
          <ProduceDetailModal listingId="list-1" onClose={() => {}} />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Sharbati Wheat")).toBeInTheDocument();
      });

      const images = screen.getAllByRole("img");
      expect(images.length).toBeGreaterThanOrEqual(2); // Main image + thumbnails
      expect(screen.getByText(/Catalog Primary Photo/i)).toBeInTheDocument();
    });

    it("renders fallback placeholder when produce lot has zero photos", async () => {
      const listingNoPhotos: ProduceListingDetail = {
        ...mockListingWithImages,
        images: [],
      };
      vi.spyOn(listingsApi, "getListing").mockResolvedValueOnce(listingNoPhotos);

      render(
        <MemoryRouter>
          <ProduceDetailModal listingId="list-1" onClose={() => {}} />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Sharbati Wheat")).toBeInTheDocument();
      });

      expect(screen.getByText(/No photographs uploaded for this produce lot/i)).toBeInTheDocument();
    });
  });
});
