import React, { useCallback, useEffect, useState } from "react";
import {
  Search,
  Tractor,
  Store,
  RotateCw,
  ChevronLeft,
  ChevronRight,
  SlidersHorizontal,
  X,
  LayoutGrid,
  Grid3X3,
  ShieldCheck,
} from "lucide-react";
import { listingsApi } from "../api/listings";
import { requirementsApi } from "../api/requirements";
import { ApiError } from "../api/errors";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/states";
import { ProduceListingCard } from "../components/marketplace/ProduceListingCard";
import { BuyerRequirementCard } from "../components/marketplace/BuyerRequirementCard";
import { ProduceDetailModal } from "../components/marketplace/ProduceDetailModal";
import { RequirementDetailModal } from "../components/marketplace/RequirementDetailModal";
import type {
  BuyerRequirementPublicSummary,
  MarketplaceListingFilterParams,
  MarketplaceRequirementFilterParams,
  ProduceCategory,
  ProduceListingPublicSummary,
} from "../types";

export const MarketplacePage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"produce" | "buyers">("produce");
  const [categories, setCategories] = useState<ProduceCategory[]>([]);

  // Search & common filters
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategoryId, setSelectedCategoryId] = useState("");
  const [locationState, setLocationState] = useState("");
  const [locationCity, setLocationCity] = useState("");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [unit, setUnit] = useState("");
  const [qualityGrade, setQualityGrade] = useState("");

  // Requirement-specific filters
  const [priceCondition, setPriceCondition] = useState("");
  const [minQuantity, setMinQuantity] = useState("");
  const [maxQuantity, setMaxQuantity] = useState("");

  // Sorting
  const [sortByProduce, setSortByProduce] = useState<
    "created_at" | "price_per_unit" | "available_quantity" | "product_name"
  >("created_at");
  const [sortByRequirements, setSortByRequirements] = useState<
    "created_at" | "required_by_date" | "required_quantity" | "target_price_per_unit" | "product_name"
  >("created_at");
  const [sortOrder, setSortOrder] = useState<"desc" | "asc">("desc");

  // View density mode
  const [viewMode, setViewMode] = useState<"grid" | "compact">("grid");

  // Pagination
  const [page, setPage] = useState(1);
  const [pageSize] = useState(12);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  // Data states
  const [produceListings, setProduceListings] = useState<ProduceListingPublicSummary[]>([]);
  const [buyerRequirements, setBuyerRequirements] = useState<BuyerRequirementPublicSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Detail modals
  const [selectedListingId, setSelectedListingId] = useState<string | null>(null);
  const [selectedRequirementId, setSelectedRequirementId] = useState<string | null>(null);

  // Mobile & Expandable filter drawer
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  // Load Categories once
  useEffect(() => {
    listingsApi
      .getCategories()
      .then((cats) => setCategories(cats))
      .catch(() => {
        // Fallback silently if categories fail to load
      });
  }, []);

  // Fetch produce catalog
  const loadProduce = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params: MarketplaceListingFilterParams = {
        q: searchQuery.trim() || undefined,
        category_id: selectedCategoryId || undefined,
        state: locationState.trim() || undefined,
        city: locationCity.trim() || undefined,
        min_price: minPrice ? Number(minPrice) : undefined,
        max_price: maxPrice ? Number(maxPrice) : undefined,
        unit: unit.trim() || undefined,
        quality_grade: qualityGrade.trim() || undefined,
        sort_by: sortByProduce,
        sort_order: sortOrder,
        page,
        page_size: pageSize,
      };

      const res = await listingsApi.searchMarketplace(params);
      setProduceListings(res.items);
      setTotalCount(res.total);
      setTotalPages(res.total_pages || 1);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message || "Failed to load marketplace produce lots.");
      } else {
        setError("Network error: Unable to reach AgriDirect marketplace.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [
    searchQuery,
    selectedCategoryId,
    locationState,
    locationCity,
    minPrice,
    maxPrice,
    unit,
    qualityGrade,
    sortByProduce,
    sortOrder,
    page,
    pageSize,
  ]);

  // Fetch buyer requirements
  const loadRequirements = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params: MarketplaceRequirementFilterParams = {
        q: searchQuery.trim() || undefined,
        category_id: selectedCategoryId || undefined,
        state: locationState.trim() || undefined,
        city: locationCity.trim() || undefined,
        min_price: minPrice ? Number(minPrice) : undefined,
        max_price: maxPrice ? Number(maxPrice) : undefined,
        min_quantity: minQuantity ? Number(minQuantity) : undefined,
        max_quantity: maxQuantity ? Number(maxQuantity) : undefined,
        unit: unit.trim() || undefined,
        quality_grade: qualityGrade.trim() || undefined,
        price_condition: priceCondition || undefined,
        sort_by: sortByRequirements,
        sort_order: sortOrder,
        page,
        page_size: pageSize,
      };

      const res = await requirementsApi.searchMarketplace(params);
      setBuyerRequirements(res.items);
      setTotalCount(res.total);
      setTotalPages(res.total_pages || 1);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message || "Failed to load buyer procurement demands.");
      } else {
        setError("Network error: Unable to reach AgriDirect demand board.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [
    searchQuery,
    selectedCategoryId,
    locationState,
    locationCity,
    minPrice,
    maxPrice,
    minQuantity,
    maxQuantity,
    unit,
    qualityGrade,
    priceCondition,
    sortByRequirements,
    sortOrder,
    page,
    pageSize,
  ]);

  useEffect(() => {
    if (activeTab === "produce") {
      void loadProduce();
    } else {
      void loadRequirements();
    }
  }, [activeTab, loadProduce, loadRequirements]);

  const handleTabSwitch = (tab: "produce" | "buyers") => {
    setActiveTab(tab);
    setPage(1);
    setError(null);
  };

  const handleResetFilters = () => {
    setSearchQuery("");
    setSelectedCategoryId("");
    setLocationState("");
    setLocationCity("");
    setMinPrice("");
    setMaxPrice("");
    setUnit("");
    setQualityGrade("");
    setPriceCondition("");
    setMinQuantity("");
    setMaxQuantity("");
    setPage(1);
  };

  // Active filter count computation
  const activeFilters = [
    searchQuery ? { label: `Search: "${searchQuery}"`, clear: () => setSearchQuery("") } : null,
    selectedCategoryId
      ? {
          label: `Category: ${categories.find((c) => c.id === selectedCategoryId)?.name || "Selected"}`,
          clear: () => setSelectedCategoryId(""),
        }
      : null,
    locationState ? { label: `State: ${locationState}`, clear: () => setLocationState("") } : null,
    locationCity ? { label: `District: ${locationCity}`, clear: () => setLocationCity("") } : null,
    minPrice || maxPrice
      ? {
          label: `Price: ₹${minPrice || 0} - ₹${maxPrice || "Max"}`,
          clear: () => {
            setMinPrice("");
            setMaxPrice("");
          },
        }
      : null,
    qualityGrade ? { label: `Grade: ${qualityGrade}`, clear: () => setQualityGrade("") } : null,
    unit ? { label: `Unit: ${unit}`, clear: () => setUnit("") } : null,
    priceCondition ? { label: `Condition: ${priceCondition}`, clear: () => setPriceCondition("") } : null,
  ].filter(Boolean) as { label: string; clear: () => void }[];

  const activeFilterCount = activeFilters.length;

  return (
    <div className="space-y-6">
      {/* Marketplace Header */}
      <div className="pb-4 border-b border-border space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-primary/10 text-primary border border-primary/20">
                <ShieldCheck className="w-3.5 h-3.5" />
                Verified B2B Direct Trade
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              AgriDirect Wholesale Marketplace
            </h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Discover verified farm produce lots and commercial procurement requirements across India
            </p>
          </div>

          {/* Dual Tab Discovery Switcher */}
          <div className="flex items-center p-1.5 rounded-2xl bg-secondary/80 border border-border w-fit shadow-2xs">
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "produce"}
              onClick={() => handleTabSwitch("produce")}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                activeTab === "produce"
                  ? "bg-card text-primary shadow-xs border border-border"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Tractor className="w-4 h-4" aria-hidden="true" />
              <span>Find Produce (Supply)</span>
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "buyers"}
              onClick={() => handleTabSwitch("buyers")}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                activeTab === "buyers"
                  ? "bg-card text-primary shadow-xs border border-border"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Store className="w-4 h-4" aria-hidden="true" />
              <span>Find Buyers (Demand)</span>
            </button>
          </div>
        </div>

        {/* Quick Category Carousel / Horizontal Pills */}
        {categories.length > 0 && (
          <div className="flex items-center gap-2 overflow-x-auto pt-2 pb-1 scrollbar-none text-xs">
            <button
              type="button"
              onClick={() => {
                setSelectedCategoryId("");
                setPage(1);
              }}
              className={`px-3.5 py-1.5 rounded-xl font-semibold whitespace-nowrap transition-all border ${
                selectedCategoryId === ""
                  ? "bg-primary text-primary-foreground border-primary shadow-xs"
                  : "bg-card text-muted-foreground border-border hover:bg-secondary hover:text-foreground"
              }`}
            >
              All Commodities
            </button>
            {categories.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => {
                  setSelectedCategoryId(selectedCategoryId === c.id ? "" : c.id);
                  setPage(1);
                }}
                className={`px-3.5 py-1.5 rounded-xl font-semibold whitespace-nowrap transition-all border ${
                  selectedCategoryId === c.id
                    ? "bg-primary text-primary-foreground border-primary shadow-xs"
                    : "bg-card text-muted-foreground border-border hover:bg-secondary hover:text-foreground"
                }`}
              >
                {c.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Main Filter & Search Controls */}
      <div className="p-4 rounded-2xl bg-card border border-border shadow-xs space-y-4">
        {/* Search Bar & Quick Controls */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-muted-foreground absolute left-3.5 top-3" aria-hidden="true" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setPage(1);
              }}
              placeholder={
                activeTab === "produce"
                  ? "Search produce lots (e.g. Sharbati Wheat, Alphonso Mango, Potatoes)..."
                  : "Search buyer procurement demands (e.g. Basmati Rice, Food-Grade Soy)..."
              }
              className="w-full pl-10 pr-9 py-2 text-sm rounded-xl border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary shadow-2xs"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => {
                  setSearchQuery("");
                  setPage(1);
                }}
                className="absolute right-3 top-2.5 text-muted-foreground hover:text-foreground p-0.5 rounded-full"
                aria-label="Clear search input"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setMobileFiltersOpen(!mobileFiltersOpen)}
              className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl border text-xs font-semibold transition-all ${
                activeFilterCount > 0 || mobileFiltersOpen
                  ? "bg-primary/10 border-primary/30 text-primary"
                  : "border-border bg-card text-foreground hover:bg-secondary"
              }`}
            >
              <SlidersHorizontal className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Filters</span>
              {activeFilterCount > 0 && (
                <span className="px-1.5 py-0.2 rounded-full bg-primary text-primary-foreground text-[10px] font-bold">
                  {activeFilterCount}
                </span>
              )}
            </button>

            <button
              type="button"
              onClick={() => (activeTab === "produce" ? void loadProduce() : void loadRequirements())}
              disabled={isLoading}
              className="p-2 rounded-xl border border-border bg-card text-foreground hover:bg-secondary transition-colors disabled:opacity-50"
              aria-label="Refresh marketplace results"
            >
              <RotateCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Expandable Filter Panel (Desktop & Mobile toggle) */}
        <div
          className={`grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 pt-3 border-t border-border ${
            mobileFiltersOpen ? "block" : "hidden sm:grid"
          }`}
        >
          {/* Category Filter */}
          <div>
            <label className="block text-[11px] font-semibold text-muted-foreground uppercase mb-1">
              Category
            </label>
            <select
              value={selectedCategoryId}
              onChange={(e) => {
                setSelectedCategoryId(e.target.value);
                setPage(1);
              }}
              className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">All Categories</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          {/* Location State */}
          <div>
            <label className="block text-[11px] font-semibold text-muted-foreground uppercase mb-1">
              {activeTab === "produce" ? "Sourcing State" : "Destination State"}
            </label>
            <input
              type="text"
              placeholder="e.g. Maharashtra, Punjab"
              value={locationState}
              onChange={(e) => {
                setLocationState(e.target.value);
                setPage(1);
              }}
              className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          {/* Location City */}
          <div>
            <label className="block text-[11px] font-semibold text-muted-foreground uppercase mb-1">
              {activeTab === "produce" ? "Sourcing District" : "Receiving Dock"}
            </label>
            <input
              type="text"
              placeholder="e.g. Nashik, Ludhiana"
              value={locationCity}
              onChange={(e) => {
                setLocationCity(e.target.value);
                setPage(1);
              }}
              className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          {/* Sort By & Direction */}
          <div>
            <label className="block text-[11px] font-semibold text-muted-foreground uppercase mb-1">
              Sort By
            </label>
            <div className="flex items-center gap-1.5">
              {activeTab === "produce" ? (
                <select
                  value={sortByProduce}
                  onChange={(e) => {
                    setSortByProduce(e.target.value as any);
                    setPage(1);
                  }}
                  className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  aria-label="Sort produce listings by"
                >
                  <option value="created_at">Recently Listed</option>
                  <option value="price_per_unit">Price per Unit</option>
                  <option value="available_quantity">Available Volume</option>
                  <option value="product_name">Produce Name</option>
                </select>
              ) : (
                <select
                  value={sortByRequirements}
                  onChange={(e) => {
                    setSortByRequirements(e.target.value as any);
                    setPage(1);
                  }}
                  className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  aria-label="Sort buyer requirements by"
                >
                  <option value="created_at">Recently Posted</option>
                  <option value="required_by_date">Deadline Date</option>
                  <option value="required_quantity">Required Volume</option>
                  <option value="target_price_per_unit">Target Price</option>
                  <option value="product_name">Demand Name</option>
                </select>
              )}
              <button
                type="button"
                onClick={() => {
                  setSortOrder((prev) => (prev === "desc" ? "asc" : "desc"));
                  setPage(1);
                }}
                className="px-2.5 py-1.5 text-xs font-semibold rounded-lg border border-border bg-background text-foreground hover:bg-secondary transition-colors whitespace-nowrap flex-shrink-0"
                title={`Sort order: ${sortOrder === "desc" ? "Descending" : "Ascending"}. Click to toggle.`}
                aria-label={`Toggle sort order direction. Currently ${sortOrder === "desc" ? "Descending" : "Ascending"}`}
              >
                {sortOrder === "desc" ? "Desc ↓" : "Asc ↑"}
              </button>
            </div>
          </div>

          {/* Price Range Filter Inputs */}
          <div>
            <label className="block text-[11px] font-semibold text-muted-foreground uppercase mb-1">
              Min Price (₹)
            </label>
            <input
              type="number"
              placeholder="e.g. 1500"
              value={minPrice}
              onChange={(e) => {
                setMinPrice(e.target.value);
                setPage(1);
              }}
              className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-muted-foreground uppercase mb-1">
              Max Price (₹)
            </label>
            <input
              type="number"
              placeholder="e.g. 6000"
              value={maxPrice}
              onChange={(e) => {
                setMaxPrice(e.target.value);
                setPage(1);
              }}
              className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          {/* Quality Grade */}
          <div>
            <label className="block text-[11px] font-semibold text-muted-foreground uppercase mb-1">
              Quality Grade
            </label>
            <input
              type="text"
              placeholder="e.g. Grade A, Organic"
              value={qualityGrade}
              onChange={(e) => {
                setQualityGrade(e.target.value);
                setPage(1);
              }}
              className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          {/* Unit of Measure */}
          <div>
            <label className="block text-[11px] font-semibold text-muted-foreground uppercase mb-1">
              Unit
            </label>
            <select
              value={unit}
              onChange={(e) => {
                setUnit(e.target.value);
                setPage(1);
              }}
              className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">All Units</option>
              <option value="quintal">Quintal</option>
              <option value="kg">Kilogram (kg)</option>
              <option value="metric_ton">Metric Ton</option>
              <option value="crate">Crate</option>
            </select>
          </div>
        </div>

        {/* Active Filters Tag Bar */}
        {activeFilters.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 pt-3 border-t border-border text-xs">
            <span className="text-muted-foreground font-medium text-[11px] uppercase tracking-wider mr-1">
              Active Filters:
            </span>
            {activeFilters.map((f, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-secondary text-foreground text-xs font-medium border border-border"
              >
                <span>{f.label}</span>
                <button
                  type="button"
                  onClick={f.clear}
                  className="hover:text-primary transition-colors p-0.5"
                  aria-label={`Remove filter ${f.label}`}
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
            <button
              type="button"
              onClick={handleResetFilters}
              className="text-xs font-semibold text-primary hover:text-primary-800 ml-2"
            >
              Reset All Filters
            </button>
          </div>
        )}
      </div>

      {/* Results Header with View Mode Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-muted-foreground px-1">
        <div className="flex items-center gap-2">
          <span>
            Showing {activeTab === "produce" ? produceListings.length : buyerRequirements.length} of{" "}
            <strong className="text-foreground">{totalCount}</strong> verified marketplace listings
          </span>
        </div>

        <div className="flex items-center gap-3">
          <span className="font-semibold text-foreground hidden sm:inline">
            {activeTab === "produce" ? "Catalog: Farm Produce Lots" : "Demand Board: Buyer Requirements"}
          </span>

          {/* Density Toggle */}
          <div className="flex items-center p-0.5 rounded-lg bg-secondary border border-border">
            <button
              type="button"
              onClick={() => setViewMode("grid")}
              className={`p-1 rounded-md transition-colors ${
                viewMode === "grid" ? "bg-card text-foreground shadow-2xs" : "text-muted-foreground hover:text-foreground"
              }`}
              title="Standard Grid View"
              aria-label="Standard Grid View"
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={() => setViewMode("compact")}
              className={`p-1 rounded-md transition-colors ${
                viewMode === "compact" ? "bg-card text-foreground shadow-2xs" : "text-muted-foreground hover:text-foreground"
              }`}
              title="Compact Grid View"
              aria-label="Compact Grid View"
            >
              <Grid3X3 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Content View */}
      {isLoading ? (
        <LoadingState
          message={
            activeTab === "produce"
              ? "Scanning agricultural wholesale catalog..."
              : "Scanning commercial procurement demand board..."
          }
        />
      ) : error ? (
        <ErrorState
          message={error}
          onRetry={() => (activeTab === "produce" ? void loadProduce() : void loadRequirements())}
        />
      ) : activeTab === "produce" ? (
        produceListings.length === 0 ? (
          <EmptyState
            title="No produce lots found"
            description="No active produce listings match your specified filters or search term."
            actionLabel="Reset Filters"
            onAction={handleResetFilters}
          />
        ) : (
          <div
            className={
              viewMode === "grid"
                ? "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
                : "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
            }
          >
            {produceListings.map((listing) => (
              <ProduceListingCard
                key={listing.id}
                listing={listing}
                onViewDetails={(item) => setSelectedListingId(item.id)}
              />
            ))}
          </div>
        )
      ) : buyerRequirements.length === 0 ? (
        <EmptyState
          title="No procurement requirements found"
          description="No active buyer procurement demands match your specified filters or search term."
          actionLabel="Reset Filters"
          onAction={handleResetFilters}
        />
      ) : (
        <div
          className={
            viewMode === "grid"
              ? "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
              : "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
          }
        >
          {buyerRequirements.map((req) => (
            <BuyerRequirementCard
              key={req.id}
              requirement={req}
              onViewDetails={(item) => setSelectedRequirementId(item.id)}
            />
          ))}
        </div>
      )}

      {/* Pagination Bar */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-6 border-t border-border text-xs text-muted-foreground">
          <span>
            Page {page} of {totalPages} ({totalCount} total listings)
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border bg-card hover:bg-secondary disabled:opacity-50 transition-colors"
            >
              <ChevronLeft className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Previous</span>
            </button>
            <span className="font-semibold text-foreground px-2">
              {page} / {totalPages}
            </span>
            <button
              type="button"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border bg-card hover:bg-secondary disabled:opacity-50 transition-colors"
            >
              <span>Next</span>
              <ChevronRight className="w-3.5 h-3.5" aria-hidden="true" />
            </button>
          </div>
        </div>
      )}

      {/* Detail Modals */}
      <ProduceDetailModal
        listingId={selectedListingId}
        onClose={() => setSelectedListingId(null)}
      />

      <RequirementDetailModal
        requirementId={selectedRequirementId}
        onClose={() => setSelectedRequirementId(null)}
      />
    </div>
  );
};
