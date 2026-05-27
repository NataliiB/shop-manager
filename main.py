from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db

app = FastAPI(title="Shop Manager API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Erlaubt Zugriffe von jeder Quelle (perfekt für die Entwicklung)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Der Python-Backend-Server runs successfull!"}

@app.get("/api/analytics/top-products")
def get_top_products(limit: int = 5, db: Session = Depends(get_db)):
    
    # Hier definierst du deinen exakten SQL-Query aus pgAdmin.
    # ':limit' ist ein Platzhalter, um SQL-Injections zu verhindern (Sicherheitsstandard).
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
    
    # Wir führen den Query aus und übergeben das dynamische Limit
    result = db.execute(query, {"limit": limit})
    
    # Da die Datenbank uns rohe Tabellenzeilen liefert, 
    # transformieren wir sie in eine Liste aus Python-Dictionaries (JSON).
    top_products_list = []
    for row in result:
        top_products_list.append({
            "product_name": row.product_name,
            "category": row.category,
            "total_units_sold": row.total_units_sold,
            "total_revenue": row.total_revenue
        })
        
    return top_products_list