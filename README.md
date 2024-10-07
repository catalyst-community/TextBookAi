# TextBookAi

## Installation and Setup

Follow the steps below to install and run the application.

### 1. Install Dependencies

Run the following command to install the necessary dependencies without installing the root package:

```bash
poetry install --no-root
```

### 2. Activate the Virtual Environment

Next, activate the Poetry shell:

```bash
poetry shell
```

### 3. Configure Environment Variables

Create a `.env` file in the project root and add your API key:

```plaintext
GEMINI_API_KEY='AIzaS...............'
```

### 4. Run the Application

Start the application using Uvicorn with live reload:

```bash
uvicorn main:app --reload
```

Now you’re ready to use TextBookAi!