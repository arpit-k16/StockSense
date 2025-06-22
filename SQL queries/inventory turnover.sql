SELECT 
  store_id,
  product_id,
  SUM(units_sold) AS total_units_sold,
  ROUND(AVG(inventory_level), 2) AS avg_inventory_level,
  ROUND(
    CAST(SUM(units_sold) AS FLOAT) / NULLIF(AVG(inventory_level), 0),
    2
  ) AS inventory_turnover
FROM inventory_forecasting
WHERE date BETWEEN DATEADD(DAY, -7, '2022-12-24') AND '2022-12-31'
GROUP BY store_id, product_id
ORDER BY inventory_turnover DESC;
