from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, update

from app.ai.provider import get_provider
from app.models import Artisan, CraftProduct, Order, UserType
from app.schemas import Money, OrderIn, OrderOut, ProductIn, ProductOut
from app.security import CurrentUser, DbSession

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


def _product_out(product: CraftProduct, artisan: Artisan) -> ProductOut:
    return ProductOut(
        id=product.id,
        name=product.name,
        name_ar=product.name_ar,
        category=product.category,
        price=Money.of(product.price_centimes),
        stock=product.stock,
        technique=product.technique,
        origin=product.origin,
        story=product.story,
        story_is_ai_drafted=product.story_is_ai_drafted,
        artisan_name=artisan.name,
        artisan_region=artisan.region,
        artisan_workshop=artisan.workshop,
    )


@router.get("/products", response_model=list[ProductOut])
def list_products(
    db: DbSession,
    category: str | None = None,
    region: str | None = None,
    in_stock_only: bool = True,
    limit: int = Query(default=40, ge=1, le=100),
) -> list[ProductOut]:
    stmt = select(CraftProduct, Artisan).join(Artisan, Artisan.id == CraftProduct.artisan_id)
    if category:
        stmt = stmt.where(CraftProduct.category == category)
    if region:
        stmt = stmt.where(Artisan.region == region)
    if in_stock_only:
        stmt = stmt.where(CraftProduct.stock > 0)
    rows = db.execute(stmt.limit(limit)).all()
    return [_product_out(p, a) for p, a in rows]


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: str, db: DbSession) -> ProductOut:
    product = db.get(CraftProduct, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    return _product_out(product, db.get(Artisan, product.artisan_id))


@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def publish_product(payload: ProductIn, user: CurrentUser, db: DbSession) -> ProductOut:
    """An artisan lists a piece; the AI drafts its story from their own notes.

    The draft is flagged so the marketplace can show it as artisan-supplied and
    AI-worded — never as invented provenance.
    """
    if user.user_type != UserType.artisan:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only artisan accounts can publish")

    artisan = db.execute(select(Artisan).where(Artisan.user_id == user.id)).scalar_one_or_none()
    if artisan is None:
        artisan = Artisan(
            name=user.name, region=user.home_region or "", craft=payload.category, user_id=user.id
        )
        db.add(artisan)
        db.flush()

    story = await get_provider().draft_product_story(
        product=payload.name,
        craft=payload.category,
        region=payload.origin or artisan.region,
        artisan=artisan.name,
        notes=payload.notes,
        language=payload.language,
    )

    product = CraftProduct(
        artisan_id=artisan.id,
        name=payload.name,
        name_ar=payload.name_ar,
        category=payload.category,
        price_centimes=payload.price_centimes,
        stock=payload.stock,
        technique=payload.technique,
        origin=payload.origin or artisan.region,
        story=story,
        story_is_ai_drafted=True,
    )
    db.add(product)
    db.commit()
    return _product_out(product, artisan)


@router.post("/orders", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def place_order(payload: OrderIn, user: CurrentUser, db: DbSession) -> OrderOut:
    product = db.get(CraftProduct, payload.product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

    # Decrement in the WHERE clause, not in Python: two buyers racing for the
    # last rug cannot both win (AC-6.2).
    result = db.execute(
        update(CraftProduct)
        .where(CraftProduct.id == product.id, CraftProduct.stock >= payload.quantity)
        .values(stock=CraftProduct.stock - payload.quantity)
    )
    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Not enough stock left")

    order = Order(
        user_id=user.id,
        product_id=product.id,
        quantity=payload.quantity,
        unit_price_centimes=product.price_centimes,
        total_centimes=product.price_centimes * payload.quantity,
    )
    db.add(order)
    db.commit()

    return OrderOut(
        id=order.id,
        product_id=product.id,
        product_name=product.name,
        quantity=order.quantity,
        unit_price=Money.of(order.unit_price_centimes),
        total=Money.of(order.total_centimes),
        status=order.status,
        created_at=order.created_at,
    )


@router.get("/orders", response_model=list[OrderOut])
def my_orders(user: CurrentUser, db: DbSession) -> list[OrderOut]:
    rows = db.execute(
        select(Order, CraftProduct)
        .join(CraftProduct, CraftProduct.id == Order.product_id)
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
    ).all()
    return [
        OrderOut(
            id=o.id,
            product_id=o.product_id,
            product_name=p.name,
            quantity=o.quantity,
            unit_price=Money.of(o.unit_price_centimes),
            total=Money.of(o.total_centimes),
            status=o.status,
            created_at=o.created_at,
        )
        for o, p in rows
    ]
