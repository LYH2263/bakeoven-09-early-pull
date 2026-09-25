"""登记实际出炉的接口测试：用 SQLite 内存库直接调用路由函数。"""

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.router import _all_occupancies, create_batch, gantt, register_actual_out, windows
from app.database import Base
from app.models.models import Batch, Oven, Product
from app.schemas.schemas import ActualOutIn, BatchCreate


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        product = Product(name="欧包", ferment_min=40, bake_min=35)  # bake [40,75]
        quick = Product(name="速烤", ferment_min=0, bake_min=35)  # 无发酵段
        oven = Oven(label="1号炉")
        session.add_all([product, quick, oven])
        session.flush()
        session.add(Batch(product_id=product.id, oven_id=oven.id, code="BO-1", start_min=0))
        session.commit()
        yield session


def _batch(session):
    return session.query(Batch).one()


def test_register_within_bake_truncates_occupancy(db):
    out = register_actual_out(_batch(db).id, ActualOutIn(actual_out_min=60), db=db)
    assert out.actual_out_min == 60
    bake = [o for o in _all_occupancies(db) if o.phase == "bake"][0]
    assert (bake.interval.start, bake.interval.end) == (40, 60)
    # 持久化：重新取仍在
    db.expire_all()
    assert _batch(db).actual_out_min == 60


def test_register_before_bake_start_rejected(db):
    bid = _batch(db).id
    with pytest.raises(HTTPException) as ei:
        register_actual_out(bid, ActualOutIn(actual_out_min=39), db=db)
    assert ei.value.status_code == 400
    assert _batch(db).actual_out_min is None


def test_register_after_original_end_rejected(db):
    bid = _batch(db).id
    with pytest.raises(HTTPException) as ei:
        register_actual_out(bid, ActualOutIn(actual_out_min=76), db=db)
    assert ei.value.status_code == 400
    assert _batch(db).actual_out_min is None


def test_gantt_bake_block_ends_at_actual_out(db):
    register_actual_out(_batch(db).id, ActualOutIn(actual_out_min=60), db=db)
    blocks = gantt(db=db)
    bake_block = [b for b in blocks if b.phase == "bake"][0]
    ferment_block = [b for b in blocks if b.phase == "ferment"][0]
    assert bake_block.end_min == 60
    assert (ferment_block.start_min, ferment_block.end_min) == (0, 40)


def test_conflict_freed_tail_allows_following_batch(db):
    # 速烤（无发酵，35 分钟）在 60 开工：未截断时与烘烤尾段 [60,75) 冲突；截断后可排入
    quick = db.query(Product).filter_by(name="速烤").one()
    oven = db.query(Oven).one()
    with pytest.raises(HTTPException) as ei:
        create_batch(BatchCreate(product_id=quick.id, oven_id=oven.id, start_min=60), db=db)
    assert ei.value.status_code == 409

    register_actual_out(_batch(db).id, ActualOutIn(actual_out_min=60), db=db)
    created = create_batch(BatchCreate(product_id=quick.id, oven_id=oven.id, start_min=60), db=db)
    assert created.code  # 尾段不再占炉，60 点半开衔接，创建成功
    assert db.query(Batch).filter_by(code=created.code).one().start_min == 60


def test_window_uses_freed_gap(db):
    # 09:00 开工：ferment [540,580)，bake [580,615)；实际出炉截到 600
    product = db.query(Product).filter_by(name="欧包").one()
    oven = db.query(Oven).one()
    db.query(Batch).delete()
    db.add(Batch(product_id=product.id, oven_id=oven.id, code="BO-9", start_min=540))
    db.commit()
    register_actual_out(_batch(db).id, ActualOutIn(actual_out_min=600), db=db)
    ws = windows(product_id=product.id, db=db)
    w = [x for x in ws if x.oven_id == oven.id][0]
    assert w.start_min == 600  # 截断后的空闲可被窗口计入；未截断时应为 615
