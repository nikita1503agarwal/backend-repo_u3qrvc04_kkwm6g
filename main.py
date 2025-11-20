import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

from database import db, create_document, get_documents

app = FastAPI(title="Emerald Flower Shop API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Emerald Flower Shop Backend is running"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# ----- Schemas endpoint for viewer -----
@app.get("/schema")
def get_schema() -> Dict[str, Any]:
    """Expose Pydantic schema definitions so external tools can read them"""
    try:
        import schemas as app_schemas
        out: Dict[str, Any] = {}
        for name in dir(app_schemas):
            obj = getattr(app_schemas, name)
            if isinstance(obj, type) and issubclass(obj, BaseModel) and obj is not BaseModel:
                model: BaseModel = obj
                out[name] = model.model_json_schema()
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----- Product Endpoints -----
class ProductIn(BaseModel):
    title: str
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    category: str
    in_stock: bool = True
    image: Optional[str] = None


@app.get("/api/products")
def list_products(limit: Optional[int] = None):
    try:
        products = get_documents("product", {}, limit)  # type: ignore
        # Seed sample products if empty
        if not products:
            samples = [
                {
                    "title": "Emerald Roses",
                    "description": "A lush bouquet of deep green-tinted roses, perfect for elegant occasions.",
                    "price": 39.0,
                    "category": "bouquet",
                    "in_stock": True,
                    "image": "/flowers/emerald-roses.jpg",
                },
                {
                    "title": "Mint Tulip Mix",
                    "description": "Soft tulips with a mint hue, bundled in recyclable wrap.",
                    "price": 29.0,
                    "category": "bouquet",
                    "in_stock": True,
                    "image": "/flowers/mint-tulips.jpg",
                },
                {
                    "title": "Jade Succulent Set",
                    "description": "Three easy-care succulents in matte emerald pots.",
                    "price": 24.0,
                    "category": "plant",
                    "in_stock": True,
                    "image": "/flowers/jade-succulents.jpg",
                },
                {
                    "title": "Forest Fern Basket",
                    "description": "A full-bodied fern in a handwoven basket.",
                    "price": 34.0,
                    "category": "plant",
                    "in_stock": True,
                    "image": "/flowers/forest-fern.jpg",
                },
            ]
            for s in samples:
                create_document("product", s)
            products = get_documents("product")
        # Convert ObjectId to string
        cleaned = []
        for p in products:
            p["_id"] = str(p.get("_id"))
            cleaned.append(p)
        return {"items": cleaned}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/products")
def create_product(data: ProductIn):
    try:
        _id = create_document("product", data)
        return {"id": _id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----- Order Endpoints -----
class OrderItem(BaseModel):
    product_id: str
    title: str
    quantity: int = Field(..., ge=1)
    price: float = Field(..., ge=0)


class CustomerInfo(BaseModel):
    name: str
    email: str


class OrderIn(BaseModel):
    items: List[OrderItem]
    total: float = Field(..., ge=0)
    customer: CustomerInfo
    note: Optional[str] = None


@app.post("/api/orders")
def create_order(order: OrderIn):
    try:
        order_dict = order.model_dump()
        order_id = create_document("order", order_dict)
        return {"id": order_id, "status": "received"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
