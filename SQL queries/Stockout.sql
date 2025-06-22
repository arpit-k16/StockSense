SELECT 
  date,
  store_id,
  product_id,
  inventory_level,
  units_sold,
  units_ordered,
  
  -- Reason for stockout
  CASE 
    WHEN units_sold > 0 AND units_ordered = 0 THEN 'No Replenishment'
    WHEN units_sold = 0 THEN 'No Demand'
    ELSE 'Likely Stock Miss'
  END AS stockout_reason,

  -- Contextual signals
  price,
  discount,
  demand_forecast,
  weather_condition,
  holiday_promotion,
  seasonality,
  competitor_pricing

FROM inventory_forecasting
WHERE inventory_level = 0
ORDER BY date, store_id, product_id;
