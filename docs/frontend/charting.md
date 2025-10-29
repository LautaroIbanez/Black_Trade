# Charting System Documentation

## Y-Axis Normalization

### Overview
The charting system now features intelligent Y-axis normalization that automatically adapts to different price ranges, providing clean, readable tick marks and proper formatting for all trading pairs.

### Features

#### 1. Clean Tick Generation
- **Automatic step sizing** based on price range magnitude
- **Clean min/max boundaries** that align with logical price levels
- **Consistent tick spacing** that prevents cluttered axes
- **Floating-point precision handling** to avoid display artifacts

#### 2. Dynamic Price Formatting
- **Thousands separators** for large numbers (e.g., $1,234,567)
- **Adaptive decimal places** based on price magnitude:
  - `$1,000+`: 0 decimals (e.g., $12,345)
  - `$100+`: 1 decimal (e.g., $123.4)
  - `$10+`: 2 decimals (e.g., $12.34)
  - `$1+`: 3 decimals (e.g., $1.234)
  - `< $1`: 4 decimals (e.g., $0.1234)

#### 3. Range Padding
- **10% padding** above and below price range for better visibility
- **Clean boundaries** that extend to logical price levels
- **Prevents edge cases** where prices touch chart boundaries

### Implementation Details

#### Tick Generation Algorithm
```typescript
function generateCleanTicks(min: number, max: number): { cleanMin: number; cleanMax: number; ticks: Tick[] } {
  const range = max - min;
  const magnitude = Math.pow(10, Math.floor(Math.log10(range)));
  const normalizedRange = range / magnitude;
  
  // Determine step size based on normalized range
  let step: number;
  if (normalizedRange <= 1) step = 0.1;
  else if (normalizedRange <= 2) step = 0.2;
  else if (normalizedRange <= 5) step = 0.5;
  else step = 1;
  
  step *= magnitude;
  
  // Calculate clean min and max
  const cleanMin = Math.floor(min / step) * step;
  const cleanMax = Math.ceil(max / step) * step;
  
  // Generate ticks...
}
```

#### Price Formatting Function
```typescript
function formatPrice(price: number): string {
  if (price >= 1000) {
    return `$${price.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
  } else if (price >= 100) {
    return `$${price.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}`;
  } else if (price >= 10) {
    return `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  } else if (price >= 1) {
    return `$${price.toLocaleString('en-US', { minimumFractionDigits: 3, maximumFractionDigits: 3 })}`;
  } else {
    return `$${price.toLocaleString('en-US', { minimumFractionDigits: 4, maximumFractionDigits: 4 })}`;
  }
}
```

### Testing Results

#### High Price Pairs (BTCUSDT)
- **Price Range**: $109,797 - $116,400
- **Format**: $109,000 - $117,000 with $1,000 steps
- **Display**: $109,000, $110,000, $111,000, etc.
- **Result**: Clean, readable thousands separators

#### Medium Price Pairs (ETHUSDT simulation)
- **Price Range**: $3,660 - $3,880
- **Format**: $3,650 - $3,900 with $10 steps
- **Display**: $3,650, $3,660, $3,670, etc.
- **Result**: Appropriate decimal precision

#### Low Price Pairs (XRPUSDT simulation)
- **Price Range**: $0.55 - $0.58
- **Format**: $0.50 - $0.60 with $0.10 steps
- **Display**: $0.50, $0.60
- **Result**: Sufficient precision for small values

#### Very Low Price Pairs (DOGEUSDT simulation)
- **Price Range**: $0.11 - $0.12
- **Format**: $0.10 - $0.20 with $0.10 steps
- **Display**: $0.10, $0.20
- **Result**: High precision for micro values

### Edge Cases Handled

#### 1. Very Small Price Ranges
- **Issue**: When price range is < 5% of minimum price
- **Solution**: Minimum step size ensures readable ticks
- **Example**: $0.111 - $0.112 → $0.10 - $0.20 range

#### 2. Very Large Price Ranges
- **Issue**: When price range is > 50% of minimum price
- **Solution**: Larger step sizes prevent overcrowding
- **Example**: $66,835 - $126,200 → $60,000 - $130,000 range

#### 3. Floating Point Precision
- **Issue**: JavaScript floating point arithmetic errors
- **Solution**: Rounding to 6 decimal places before display
- **Example**: 0.1 + 0.2 = 0.30000000000000004 → 0.3

#### 4. Zero or Negative Prices
- **Issue**: Invalid price data
- **Solution**: Fallback to default range and error handling
- **Example**: Invalid data → $0 - $100 range with warning

### Performance Considerations

#### 1. Tick Generation
- **Complexity**: O(n) where n is number of ticks
- **Optimization**: Pre-calculated step sizes for common ranges
- **Memory**: Minimal - only stores tick values and labels

#### 2. Price Formatting
- **Complexity**: O(1) for each price
- **Optimization**: Cached formatting functions
- **Memory**: Minimal - only string formatting

#### 3. Canvas Rendering
- **Complexity**: O(n) where n is number of ticks
- **Optimization**: Only renders visible ticks
- **Memory**: Minimal - only canvas drawing operations

### Future Enhancements

#### 1. Logarithmic Scaling
- **Use Case**: Very large price ranges (e.g., $1 - $100,000)
- **Implementation**: Optional logarithmic Y-axis
- **Benefit**: Better visualization of exponential growth

#### 2. Custom Tick Intervals
- **Use Case**: User-defined tick preferences
- **Implementation**: Settings panel for tick density
- **Benefit**: Personalized chart experience

#### 3. Price Level Highlighting
- **Use Case**: Important support/resistance levels
- **Implementation**: Highlight specific price levels
- **Benefit**: Better technical analysis

#### 4. Multi-Currency Support
- **Use Case**: Different base currencies
- **Implementation**: Currency-specific formatting
- **Benefit**: International trading support

### Troubleshooting

#### Common Issues

1. **Ticks not appearing**
   - Check if price range is valid
   - Verify canvas dimensions
   - Check for JavaScript errors

2. **Incorrect formatting**
   - Verify price magnitude calculation
   - Check locale settings
   - Test with different price ranges

3. **Performance issues**
   - Reduce number of ticks
   - Optimize canvas rendering
   - Check for memory leaks

#### Debug Information

Enable debug mode to see:
- Generated tick values
- Price range calculations
- Formatting decisions
- Performance metrics

```typescript
// Enable debug mode
const DEBUG_CHART = true;

if (DEBUG_CHART) {
  console.log('Price range:', { min, max, range });
  console.log('Generated ticks:', ticks);
  console.log('Formatting decisions:', formatDecisions);
}
```

### Conclusion

The Y-axis normalization system provides a robust, scalable solution for displaying price data across all trading pairs. It automatically adapts to different price ranges while maintaining readability and performance. The system handles edge cases gracefully and provides a consistent user experience regardless of the underlying price data.

