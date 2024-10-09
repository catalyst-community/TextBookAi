from fastapi import HTTPException
import psycopg2
from passlib.context import CryptContext

# Password hashing settings
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Function to hash password
def hash_password(password: str):
    return pwd_context.hash(password)


# Function to verify hashed password
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


# PostgreSQL connection setup
def get_db_connection():
    try:
        conn = psycopg2.connect(
            database="myapp_db",
            user="myapp_user",
            password="your_password",
            host="localhost",
            port="5432",
        )
        return conn
    except psycopg2.DatabaseError as e:
        print(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")
