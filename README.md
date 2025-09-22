# Inventory Intelligence Analyzer

Analyzes supplier inventory by comparing prices against Walmart retail prices. Categorizes items as Good/Okay/Bad deals for discount stores based on margin potential.

## Business Context

Regional discount stores typically sell products at 30-70% below traditional retail prices, using Walmart as their primary pricing benchmark. Their wholesale buying formula:

- **Purchase at**: Walmart retail price × 10-25%
- **Sell at**: ~50% of Walmart retail price
- **Target margin**: ~100% (double their money)

## Quick Setup

1. **Install dependencies:**

   ```bash
   poetry install
   ```

2. **Configure API access:**
   Edit `config.py` with your Walmart API credentials:

   ```python
   WALMART_CONSUMER_ID = "your_actual_consumer_id"
   WALMART_PRIVATE_KEY_PATH = "/path/to/your/walmart_key.pem"
   ```

3. **Run analysis:**
   ```bash
   poetry run python inventory_analyzer.py
   ```

## How It Works

### Multi-Tier Price Discovery

1. **UPC Exact Match** - Queries UPCitemdb API for precise product matches
2. **Direct Walmart API** - Backup lookup using official Walmart data
3. **Fuzzy Name Matching** - Searches by product description when UPC fails

### Price Categorization

Based on discount percentage from Walmart retail price:

- **Good Price (>75% off)**: Excellent margins for discount stores
- **Okay Price (60-75% off)**: Acceptable margins for volume purchases
- **Bad Price (<60% off)**: Insufficient margin for discount model
- **No Price Found**: Requires manual research

### Output Files:

- **`inventory_analysis_results.csv`**: Complete analysis with retail prices, links, and categories
- **`inventory_analysis.log`**: Processing details and API call logs
- **Console report**: Summary statistics and top deals

## Architecture

**Modular Design:**

- `InventoryAnalyzer` - Main processing engine
- `WalmartAuth` - API authentication
- `ProductSearchEnhancer` - Fuzzy search implementation

**Key Features:**

- Caching to prevent duplicate API calls
- Rate limiting for API compliance
- Graceful error handling and fallbacks
- Scalable for large inventories

Results saved to `inventory_analysis_results.csv` with all pricing data and business categorizations.
