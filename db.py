from passlib.context import CryptContext

# Password hashing settings
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Function to hash password
def hash_password(password: str):
    return pwd_context.hash(password)


# Function to verify hashed password
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)
