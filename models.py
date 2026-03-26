class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password = Column(String)
    credits = Column(Integer, default=50)
    plan = Column(String, default="free")
    is_admin = Column(Boolean, default=False)