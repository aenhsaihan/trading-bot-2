# UX Issues & Future Improvements

## Chart Historical Data Limitation

### Issue
The price chart doesn't show enough historical data. Currently limited to 100 candles, which for 1h timeframe is only ~4 days of history. Users expect to see more historical context.

### Current State
- **Fixed limit**: 100 candles (hardcoded)
- **For 1h timeframe**: Only ~4 days of history
- **Backend supports**: Up to 1000 candles
- **User expectation**: See weeks/months of history for better context

### Potential Solutions

1. **Dynamic limit based on timeframe** ✅ (Partially implemented)
   - 1h: 500 candles (~21 days)
   - 1d: 365 candles (~1 year)
   - Could increase to 1000 for maximum history

2. **User-configurable history range**
   - Add UI control: "Show last X days/weeks/months"
   - Let users choose how much history they want
   - Remember preference in localStorage

3. **Progressive loading**
   - Load initial 500 candles
   - "Load More" button to fetch additional history
   - Lazy load older data as user scrolls left

4. **Smart defaults**
   - Auto-adjust based on timeframe
   - 1m/5m: Show last 24 hours
   - 1h: Show last 30 days
   - 1d: Show last 1 year
   - 1w: Show last 2 years

5. **Date range picker**
   - Allow users to select specific date range
   - "From/To" date selection
   - More precise control over what data to display

### User Feedback Considerations
- Some users may want maximum history (1000 candles)
- Others may prefer faster loading with less data
- Mobile users may need different limits due to performance
- Consider adding a "Performance Mode" toggle

### Implementation Priority
- **Low** - Chart works, just needs more data
- Can be addressed when improving chart features
- Consider as part of larger chart enhancement effort

### Related Files
- `frontend/src/components/MarketIntelligence.tsx` - Data fetching
- `frontend/src/services/api.ts` - API call with limit parameter
- `backend/api/routes/market_data.py` - Backend limit (max 1000)

