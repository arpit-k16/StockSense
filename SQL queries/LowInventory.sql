use inventory;

WITH avg_demand AS (
    SELECT 
        store_id,
        product_id,
        AVG(units_sold) AS avg_units_sold
    FROM inventory_forecasting
    WHERE date BETWEEN DATEADD(DAY, -7, '2022-12-24') AND '2022-12-31'
    GROUP BY store_id, product_id
)

SELECT 
    inv.date,
    inv.store_id,
    inv.product_id,
    inv.inventory_level,
    inv.units_sold,
    inv.units_ordered,
    avg.avg_units_sold,
    inv.price,
    inv.discount,
    inv.demand_forecast,
    inv.weather_condition,
    inv.seasonality,
    inv.holiday_promotion,
    inv.competitor_pricing
FROM inventory_forecasting inv
JOIN avg_demand avg
  ON inv.store_id = avg.store_id 
 AND inv.product_id = avg.product_id
WHERE inv.date = '2022-12-24' 
  AND inv.inventory_level < avg.avg_units_sold
ORDER BY avg.avg_units_sold DESC;
