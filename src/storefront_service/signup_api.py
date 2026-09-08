from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from .infrai_captcha import CaptchaClient, InfraiError
from .order_ledger import OrderStatus, StoreLedger


class SignupRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    widget_record_id: str = Field(min_length=1)
    captcha_token: str = Field(min_length=1)
    captcha_vendor: str | None = None


class CustomerView(BaseModel):
    customer_id: str
    email: EmailStr


class CheckoutRequest(BaseModel):
    customer_id: str
    sku: str = Field(min_length=1)
    quantity: int = Field(ge=1, le=20)


class OrderView(BaseModel):
    order_id: str
    status: Literal["checked_out", "fulfilled"]
    receipt_id: str | None
    updates: list[str]


def create_app(captcha: CaptchaClient | None = None, ledger: StoreLedger | None = None) -> FastAPI:
    store = ledger or StoreLedger()
    supplied_client = captcha

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if supplied_client is None:
            app.state.captcha = CaptchaClient.from_environment()
        yield
        if supplied_client is None:
            await app.state.captcha.close()

    app = FastAPI(title="Captcha-gated storefront", lifespan=lifespan)
    if supplied_client is not None:
        app.state.captcha = supplied_client

    def captcha_client(request: Request) -> CaptchaClient:
        return request.app.state.captcha

    @app.post("/signup", response_model=CustomerView, status_code=201)
    async def signup(
        body: SignupRequest,
        request: Request,
        verifier: CaptchaClient = Depends(captcha_client),
    ) -> CustomerView:
        try:
            await verifier.verify(
                widget_record_id=body.widget_record_id,
                token=body.captcha_token,
                vendor=body.captcha_vendor,
                ip=request.client.host if request.client else None,
                action="signup",
                score_threshold=0.7,
            )
        except InfraiError as exc:
            client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
            raise HTTPException(status_code=client_status, detail={"code": exc.code}) from exc
        customer = store.register(str(body.email), body.name)
        return CustomerView(customer_id=customer.id, email=customer.email)

    @app.post("/checkout", response_model=OrderView, status_code=201)
    async def checkout(body: CheckoutRequest) -> OrderView:
        try:
            order = store.checkout(body.customer_id, body.sku, body.quantity)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="customer not found") from exc
        return _order_view(order)

    @app.post("/orders/{order_id}/fulfill", response_model=OrderView)
    async def fulfill(order_id: str) -> OrderView:
        try:
            return _order_view(store.fulfill(order_id))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="order not found") from exc

    @app.get("/orders/{order_id}", response_model=OrderView)
    async def order_updates(order_id: str) -> OrderView:
        try:
            return _order_view(store.orders[order_id])
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="order not found") from exc

    return app


def _order_view(order: object) -> OrderView:
    from .order_ledger import Order

    assert isinstance(order, Order)
    return OrderView(
        order_id=order.id,
        status=order.status.value,
        receipt_id=order.receipt_id,
        updates=list(order.updates),
    )


app = create_app()
