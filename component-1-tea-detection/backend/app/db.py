import datetime as dt
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from . import config

_is_sqlite = config.DATABASE_URL.startswith("sqlite")
engine = create_engine(config.DATABASE_URL,
                       connect_args={"check_same_thread": False} if _is_sqlite else {},
                       pool_pre_ping=True)
Session = sessionmaker(bind=engine)
Base = declarative_base()


def now():
    return dt.datetime.now(dt.timezone.utc)


class Mission(Base):
    __tablename__ = "missions"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    started_at = Column(DateTime, default=now)
    ended_at = Column(DateTime, nullable=True)


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    mission_id = Column(Integer, ForeignKey("missions.id"), nullable=True)
    ts = Column(DateTime, default=now)
    lat = Column(Float); lon = Column(Float); alt = Column(Float)
    decision = Column(String(16)); reason = Column(String(200)); spray_status = Column(String(8))
    tea_conf = Column(Float); person_conf = Column(Float); animal_conf = Column(Float)
    shadow_ratio = Column(Float); enh_method = Column(String(16))
    tea_before = Column(Float); tea_after = Column(Float)
    latency_ms = Column(Float); image_url = Column(String(200))


class DetectionRow(Base):
    __tablename__ = "detections"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"))
    cls = Column(String(32)); conf = Column(Float)
    x1 = Column(Integer, nullable=True); y1 = Column(Integer, nullable=True)
    x2 = Column(Integer, nullable=True); y2 = Column(Integer, nullable=True)


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True)
    ts = Column(DateTime, default=now)
    priority = Column(String(10)); message = Column(String(200))
    lat = Column(Float); lon = Column(Float)
    acked = Column(Boolean, default=False)


class SprayTest(Base):
    __tablename__ = "spray_tests"
    id = Column(Integer, primary_key=True)
    ts = Column(DateTime, default=now)
    scenario = Column(String(200)); expected = Column(String(8)); actual = Column(String(8))
    passed = Column(Boolean); response_ms = Column(Float)


class GpsLog(Base):
    __tablename__ = "gps_log"
    id = Column(Integer, primary_key=True)
    ts = Column(DateTime, default=now)
    lat = Column(Float); lon = Column(Float); alt = Column(Float)
    sats = Column(Integer); hdop = Column(Float); source = Column(String(12))
    
class Setting(Base):
    __tablename__ = "settings"
    key = Column(String(50), primary_key=True)
    value = Column(Float)
    updated_at = Column(DateTime, default=now, onupdate=now)

Base.metadata.create_all(engine)


def row_to_dict(row):
    out = {}
    for c in row.__table__.columns:
        v = getattr(row, c.name)
        out[c.name] = v.isoformat() if isinstance(v, dt.datetime) else v
    return out