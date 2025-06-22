SELECT
  date,
  store_id,
  product_id,
  units_sold,
  demand_forecast,
  (units_sold - demand_forecast) AS forecast_deviation,

  CASE 
    WHEN (units_sold - demand_forecast) > 20 THEN 'Underforecasted'
    WHEN (units_sold - demand_forecast) < -20 THEN 'Overforecasted'
    ELSE 'Accurate'
  END AS forecast_accuracy_flag,

  price,
  discount,
  Holiday_Promotion,
  weather_condition,
  seasonality
FROM inventory_forecasting
ORDER BY forecast_deviation DESC;
