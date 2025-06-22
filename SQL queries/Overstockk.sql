SELECT 
  store_id,
  product_id,
  AVG(inventory_level) AS avg_inventory_7d,
  SUM(units_sold) AS total_units_sold_7d,

  ROUND(
    CASE 
      WHEN SUM(units_sold) = 0 THEN NULL
      ELSE AVG(inventory_level) / NULLIF(SUM(units_sold), 0)
    END, 2
  ) AS stock_to_sales_ratio,

  
  CASE
    WHEN SUM(units_sold) = 0 AND AVG(inventory_level) > 100 THEN 'Stagnant Inventory'
    WHEN AVG(inventory_level) / NULLIF(SUM(units_sold), 1) > 5 THEN 'Overstocked'
    ELSE 'Normal'
  END AS inventory_health_flag

FROM inventory_forecasting
WHERE date BETWEEN DATEADD(DAY, -7, '2022-12-24') AND '2022-12-31'
GROUP BY store_id, product_id
ORDER BY stock_to_sales_ratio DESC;
