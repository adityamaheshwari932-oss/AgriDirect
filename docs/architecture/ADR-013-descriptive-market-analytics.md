# ADR-013: Descriptive Market Analytics and Statistical Disclosure Controls

**Status:** Accepted & Verified  
**Date:** 2026-11-02  

## 1. Context

AgriDirect facilitates direct commercial trade between verified farmers and commercial buyers. To empower participants to make informed commercial decisions and provide administrative oversight, the platform requires descriptive market analytics (SRS Section 4.17, FR-ANA-01 through FR-ANA-08; DFD Process 8.0, subprocesses 8.1–8.6).

In agricultural B2B trade, publishing raw transaction records or unrestrained price aggregates poses acute commercial and privacy risks:
1. **Participant De-anonymization & Inference**: In localized, thin, or concentrated markets (small towns or specialty crops), an observer can infer proprietary purchase volumes, farm yields, or negotiated prices of specific participants.
2. **Dominance Skewing**: If a single dominant buyer or farmer contributes the majority of a commodity's trade, published statistics reflect that participant's private terms rather than broader market conditions.
3. **Point Isolation on Extrema**: Publishing minimum or maximum trade prices allows counter-parties to isolate individual bids or distress sales.
4. **Fulfillment Audit Discrepancies**: In procurement demand, buyers post requirements that may subsequently be closed or soft-deleted after receiving partial deliveries. If approved fulfillments are discarded upon requirement deletion, historical trade accounting becomes corrupted.
5. **Trade Execution vs. Settlement Disconnect**: Completed orders represent legally binding, fulfilled trades. Off-platform payment complaints or delays must not erase realized trade statistics, but payment tracking details must not leak into public commodity summaries.

Furthermore, project business rules strictly mandate:
- **BR-16**: Purely descriptive analytics; predictive ML forecasting is explicitly prohibited.
- **Read-Only Invariant**: Analytics operations must be strictly read-only and never mutate persistent marketplace state.
- **ADR-002**: Synchronous SQLAlchemy 2.x ORM execution with parameterized queries.

---

## 2. Decision

We implement **Backend Module 9: Descriptive Market Analytics** according to the approved **Version 2.5 Architecture Baseline**:

### 2.1 Zero Schema Migrations
Module 9 requires zero new database tables or schema migrations. All analytical queries execute across existing, production-active tables: `produce_listings`, `produce_categories`, `buyer_requirements`, `requirement_fulfillment_approvals`, `orders`, `order_items`, `payment_records`, `ratings_reviews`, `users`, `farmer_profiles`, and `buyer_profiles`.

### 2.2 Domain Separation & Public Privacy Guarantees
1. **Public Market Summary (`GET /api/v1/analytics/market-summary`)**:
   - Aggregates active listed supply (`ProduceListing`) and realized trades (`OrderItem` join `Order` where `status = 'completed'`).
   - Realized trades include completed orders with pending or disputed payment records; cancelled orders are excluded.
   - Payment settlement totals are strictly excluded from public market summaries.
   - Category attribution references `ProduceListing.category_id` (fallback `BuyerRequirement.category_id`), explicitly identified with `category_attribution_source: "current_listing_metadata_approximate"` and `is_historical_snapshot: false`.
2. **Public Demand Summary (`GET /api/v1/analytics/demand-summary`)**:
   - Aggregates active buyer procurement demands (`BuyerRequirement`).
   - Audits permanently retained approved fulfillment volume from `RequirementFulfillmentApproval`.
   - **Permanent Retention Policy**: Approved fulfillment records are permanently retained even if parent requirements are closed or soft-deleted. Soft-deleted residual unfulfilled demand is excluded from active and closed residual demand.
3. **Authenticated Performance Dashboard (`GET /api/v1/analytics/my-performance`)**:
   - Role-specialized dashboard for active farmers and commercial buyers.
   - Order outcome rates classify orders into `pending_confirmation`, `in_progress`, `completed`, `cancelled`, and `currently_disputed`.
   - **Version 2.1 Two-Tier Denominator Model**:
     - **Tier 1 (All Placed Orders Denominator: $N_{\text{total}}$)**:
       $$\text{completed\_order\_share} = \frac{N_{\text{completed}}}{N_{\text{total}}} \times 100\%$$
       $$\text{in\_progress\_share} = \frac{N_{\text{in\_progress}}}{N_{\text{total}}} \times 100\%$$
       $$\text{pending\_share} = \frac{N_{\text{pending}}}{N_{\text{total}}} \times 100\%$$
       $$\text{dispute\_frequency} = \frac{N_{\text{disputed}}}{N_{\text{total}}} \times 100\%$$
       $$\text{cancelled\_order\_share} = \frac{N_{\text{cancelled}}}{N_{\text{total}}} \times 100\%$$
     - **Tier 2 (Concluded Outcomes Denominator: $N_{\text{concluded}} = N_{\text{completed}} + N_{\text{cancelled}}$)**:
       $$\text{concluded\_completion\_rate} = \frac{N_{\text{completed}}}{N_{\text{completed}} + N_{\text{cancelled}}} \times 100\%$$
       $$\text{concluded\_cancellation\_rate} = \frac{N_{\text{cancelled}}}{N_{\text{completed}} + N_{\text{cancelled}}} \times 100\%$$
   - Personal payment settlement breakdown reports recorded, acknowledged, disputed, and pending payment amounts, alongside average acknowledgement delay in hours.
4. **Platform Administrative Analytics (`GET /api/v1/analytics/admin/platform`)**:
   - Administrator-only overview reporting platform GMV (completed orders), pipeline GMV (in-progress orders), active inventory valuation, system-wide order lifecycle breakdown, payment settlement velocities, and user engagement composition.
   - Mounted also at alias path `GET /api/v1/admin/analytics/platform`.

---

## 3. Statistical Privacy & Disclosure Control Engine (Version 2.5)

For all public aggregate endpoints, the following sequential disclosure rules are enforced:

### 3.1 Coarse Count Banding
To prevent exact participant enumeration, suppressed or low-count slices replace exact counts with standardized coarse bands:
- $n \le 0 \implies \text{"0"}$
- $n \in \{1, 2\} \implies \text{"1–2"}$
- $3 \le n \le 5 \implies \text{"3–5"}$
- $6 \le n \le 10 \implies \text{"6–10"}$
- $n \ge 11 \implies \text{"11+"}$

### 3.2 Diversity Thresholds
For a realized trade slice:
- $k_{\text{farmers}} \ge 3$ distinct selling farmers.
- $k_{\text{buyers}} \ge 3$ distinct purchasing buyers.
- $N_{\text{trades}} \ge 3$ distinct completed orders.

If any diversity condition fails:
- Sensitive metrics (`total_quantity_traded`, `total_gross_value`, `vwap`, `arithmetic_mean_price`, `median_price`, `min_price`, `max_price`) are set to `None`.
- Exact count fields are set to `None` and substituted with coarse count bands.
- `privacy.is_suppressed = True` with `suppression_reason = "INSUFFICIENT_PARTICIPANTS"`.

### 3.3 Metric-Specific Participant Dominance Suppression
When diversity passes, individual metrics are evaluated for participant concentration:
1. **Traded Quantity Dominance**: If $\max_f (Q_f / Q_{\text{total}}) \ge 0.50$ or $\max_b (Q_b / Q_{\text{total}}) \ge 0.50$, then `total_quantity_traded = None` and `quantity_suppressed = True`.
2. **Traded Monetary Dominance**: If $\max_f (M_f / M_{\text{total}}) \ge 0.50$ or $\max_b (M_b / M_{\text{total}}) \ge 0.50$, then `total_gross_value = None` and `gross_value_suppressed = True`.
3. **VWAP Joint Dominance**: Volume-Weighted Average Price requires *both* quantity and monetary concentration $< 0.50$. If either is suppressed, `vwap = None` and `vwap_suppressed = True`.
4. **Arithmetic Mean Influence**: Evaluated across transaction line items. If any participant's observation count share $\ge 0.50$ OR price-sum share $\ge 0.50$, then `arithmetic_mean_price = None` and `arithmetic_mean_suppressed = True`.
5. **Median Dominance & Point Ownership**:
   - If any participant's observation share $\ge 0.50$, median is suppressed.
   - Point-ownership check: If the median observation item (or middle items in even-length distributions) is owned by a participant whose total observation share $\ge 0.40$, then `median_price = None` and `median_suppressed = True`.
6. **Extrema Point Isolation Protection ($P_{\min}, P_{\max}$)**:
   - Sample size depth requirement: requires $k_{\text{farmers}} \ge 5$ AND $k_{\text{buyers}} \ge 5$.
   - Clustering check: $P_{\min}$ requires at least 2 distinct farmers AND 2 distinct buyers having trades within $[P_{\min}, 1.02 P_{\min}]$. Otherwise `min_price = None`.
   - $P_{\max}$ requires at least 2 distinct farmers AND 2 distinct buyers having trades within $[0.98 P_{\max}, P_{\max}]$. Otherwise `max_price = None`.

### 3.4 Geographic Fallback
When a query specifies a `city` filter that does not meet diversity thresholds ($k_f < 3$ or $k_b < 3$), the analytics engine automatically broadens the query to `state`. The response metadata records `geographic_level_applied: "state"` and `geographic_fallback_triggered: True`.

---

## 4. Read-Only Transaction Enforcement

To guarantee zero accidental or malicious state mutation during analytical queries:
1. Dedicated FastAPI dependency `get_read_only_db` yields sessions.
2. In PostgreSQL environments, `SET TRANSACTION READ ONLY` is executed on connection acquisition.
3. An ORM `before_flush` event listener intercepts any flush or write attempt and immediately raises `RuntimeError("Data mutations are strictly prohibited in read-only analytics sessions.")`.
4. In `finally`, sessions are rolled back and closed.

---

## 5. Consequences

### Positive
- Marketplace participants receive rich, unit-safe market supply and demand visibility without leaking proprietary negotiation terms.
- Commercial participants are protected against inference and dominance attacks.
- Exact traceability to real orders and fulfillment audits without synthetic distortion or ML forecasting.
- Read-only guarantees eliminate side-effect risks in database infrastructure.

### Trade-offs & Limitations
- Dominance suppression will withhold VWAP and totals in highly concentrated specialty crop markets until additional participants join.
- Arithmetic mean and median are independently protected, occasionally causing mean to be published while median is suppressed (or vice versa), which is statistically transparent and intentional.

