use inventory;
SELECT 
  date,
  store_id,
  product_id,
  inventory_level,
  units_sold,
  units_ordered
FROM inventory_forecasting
ORDER BY date, store_id, product_id;
