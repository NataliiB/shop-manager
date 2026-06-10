from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from fastapi.responses import HTMLResponse
from datetime import datetime

app = FastAPI(title="Shop Manager API")

# CORS-Einstellungen für die reibungslose Kommunikation zwischen Frontend und API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/analytics/top-products")
def get_top_products(limit: int = 5, db: Session = Depends(get_db)):
    query = text("""
        SELECT 
            p.product_name,
            p.category,
            SUM(oi.quantity)::INT AS total_units_sold,
            SUM(oi.quantity * oi.price_at_purchase)::FLOAT AS total_revenue
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        GROUP BY p.product_id, p.product_name, p.category
        ORDER BY total_revenue DESC
        LIMIT :limit;
    """)
    result = db.execute(query, {"limit": limit})
    
    top_products_list = []
    for row in result:
        top_products_list.append({
            "product_name": row.product_name,
            "category": row.category,
            "total_units_sold": row.total_units_sold,
            "total_revenue": row.total_revenue
        })
    return top_products_list

@app.get("/api/analytics/revenue/monthly")
def get_monthly_revenue(year: int = 2026, month: int = 3, db: Session = Depends(get_db)):
    query = text("""
        SELECT 
            SUM(oi.quantity * oi.price_at_purchase)::FLOAT AS total_revenue
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        WHERE EXTRACT(YEAR FROM o.order_date) = :year 
          AND EXTRACT(MONTH FROM o.order_date) = :month;
    """)
    result = db.execute(query, {"year": year, "month": month}).fetchone()
    revenue = result[0] if result and result[0] is not None else 0.0
    return {"year": year, "month": month, "total_revenue": revenue}

@app.get("/api/analytics/products/flop-five")
def get_flop_products(db: Session = Depends(get_db)):
    query = text("""
        SELECT p.product_name, SUM(oi.quantity)::INT AS units_sold
        FROM products p
        JOIN order_items oi ON p.product_id = oi.product_id
        GROUP BY p.product_name
        ORDER BY units_sold ASC
        LIMIT 5;
    """)
    result = db.execute(query)
    
    flop_list = []
    for row in result:
        flop_list.append({
            "product_name": row.product_name,
            "units_sold": row.units_sold
        })
    return flop_list

@app.get("/api/analytics/revenue/monthly-trend")
def get_monthly_trend(db: Session = Depends(get_db)):
    current_year = datetime.now().year
    current_month = datetime.now().month

    query = text("""
        SELECT 
            EXTRACT(YEAR FROM o.order_date)::INT AS order_year,
            EXTRACT(MONTH FROM o.order_date)::INT AS order_month,
            SUM(oi.quantity * oi.price_at_purchase)::FLOAT AS total_revenue
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        WHERE NOT (EXTRACT(YEAR FROM o.order_date) = :cur_year AND EXTRACT(MONTH FROM o.order_date) = :cur_month)
        GROUP BY order_year, order_month
        ORDER BY order_year ASC, order_month ASC;
    """)
    result = db.execute(query, {"cur_year": current_year, "cur_month": current_month})
    
    trend_list = []
    for row in result:
        label = f"{row.order_month:02d}/{row.order_year}"
        trend_list.append({
            "month": label,
            "revenue": row.total_revenue
        })
    return trend_list

@app.get("/api/analytics/revenue/average-order")
def get_average_order_value(year: int = 2026, month: int = 3, db: Session = Depends(get_db)):
    query = text("""
        WITH order_sums AS (
            SELECT oi.order_id, SUM(oi.quantity * oi.price_at_purchase) AS total_sum
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            WHERE EXTRACT(YEAR FROM o.order_date) = :year
              AND EXTRACT(MONTH FROM o.order_date) = :month
            GROUP BY oi.order_id
        )
        SELECT AVG(total_sum)::FLOAT FROM order_sums;
    """)
    result = db.execute(query, {"year": year, "month": month}).fetchone()
    aov = result[0] if result and result[0] is not None else 0.0
    return {"year": year, "month": month, "average_order_value": aov}

@app.get("/api/analytics/metrics/order-volume")
def get_order_volume(year: int = 2026, month: int = 3, db: Session = Depends(get_db)):
    query = text("""
        SELECT COUNT(DISTINCT order_id)
        FROM orders
        WHERE EXTRACT(YEAR FROM order_date) = :year
          AND EXTRACT(MONTH FROM order_date) = :month;
    """)
    result = db.execute(query, {"year": year, "month": month}).fetchone()
    count = result[0] if result and result[0] is not None else 0
    return {"order_volume": count}

@app.get("/api/analytics/metrics/items-per-basket")
def get_items_per_basket(year: int = 2026, month: int = 3, db: Session = Depends(get_db)):
    query = text("""
        WITH order_sums AS (
            SELECT SUM(oi.quantity) as order_sum
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            WHERE EXTRACT(YEAR FROM o.order_date) = :year
              AND EXTRACT(MONTH FROM o.order_date) = :month
            GROUP BY o.order_id
        )
        SELECT AVG(order_sum) FROM order_sums;
    """)
    result = db.execute(query, {"year": year, "month": month}).fetchone()
    avg_items = result[0] if result and result[0] is not None else 0.0
    return {"items_per_basket": round(avg_items, 1)}

@app.get("/api/analytics/metrics/category-revenue")
def get_category_revenue(db: Session = Depends(get_db)):
    query = text("""
        SELECT p.category,
               SUM(oi.price_at_purchase * oi.quantity)::FLOAT AS category_revenue
        FROM order_items oi 
        JOIN products p ON oi.product_id = p.product_id
        GROUP BY p.category;
    """)
    result = db.execute(query)
    
    categories = []
    for row in result:
        categories.append({
            "category": row.category,
            "revenue": row.category_revenue
        })
    return categories