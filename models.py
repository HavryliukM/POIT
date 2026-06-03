from sqlalchemy import Column, Integer, Float, String, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./database.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class SensorReading(Base):
    __tablename__ = "readings"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    temp = Column(Float, nullable=False)
    hum = Column(Float, nullable=False)
    target_temp = Column(Float, nullable=True)
    actuator = Column(Integer, default=0) # 0 = OFF, 1 = ON
    state = Column(String, nullable=False)
    light = Column(Integer, default=0) # 0 = shadow, 1 = direct light
    light_val = Column(Integer, default=0) # raw ADC value

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "temp": self.temp,
            "hum": self.hum,
            "target_temp": self.target_temp,
            "actuator": self.actuator,
            "state": self.state,
            "light": self.light,
            "light_val": self.light_val,
        }


class SavedSession(Base):
    __tablename__ = "saved_sessions"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    data = Column(String, nullable=False) # JSON data of the session

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "data": self.data
        }


Base.metadata.create_all(bind=engine)
