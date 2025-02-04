from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
pwd_context.update(bcrypt__default_rounds=6)

class Hasher():
    @staticmethod
    def verify_hash(plain_data, hashed_data):
        return pwd_context.verify(plain_data, hashed_data)

    @staticmethod
    def get_hash(data):
        return pwd_context.hash(data)
    