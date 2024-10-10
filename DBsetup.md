# **PostgreSQL Database Setup**

## **Prerequisites**
- PostgreSQL installed
- psql (PostgreSQL Shell) available

## **Steps to Create and Configure the Database**

### 1. **Connect to PostgreSQL**

Access the PostgreSQL shell (psql):

```bash
psql -U postgres
```

Enter the PostgreSQL superuser password when prompted.

### 2. **Create a New Database**

Create the `myapp_db` database:

```sql
CREATE DATABASE myapp_db;
```

### 3. **Create a New User**

Create a new user for the application:

```sql
CREATE USER myapp_user WITH PASSWORD 'password';
```

> **Note**: Replace `'password'` with your desired password.

### 4. **Grant Privileges to the User**

Grant all privileges on the database `myapp_db` to the user `myapp_user`:

```sql
GRANT ALL PRIVILEGES ON DATABASE myapp_db TO myapp_user;
```

Grant all privileges on the `public` schema:

```sql
GRANT ALL PRIVILEGES ON SCHEMA public TO myapp_user;
```

### 5. **Connect to the `myapp_db` Database**

Exit the current session and connect to the `myapp_db` database as the user `myapp_user`:

```bash
psql -d myapp_db -U myapp_user
```

### 6. **Create the `authentication` Table**

Once connected to the `myapp_db` database, create the `authentication` table:

```sql
CREATE TABLE authentication (
    emailid VARCHAR(255) PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);
```


and change the mock database connection in main.py to :

```code
# Mock database connection function
def get_db_connection():
    return psycopg2.connect(
        database="myapp_db",
        user="myapp_user",
        password="password",
        host="localhost",
    )
```