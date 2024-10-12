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
GEMINI_API_KEY=AIzaS...............
```

### 4. Run the Application

Start the application using Uvicorn with live reload:

```bash
uvicorn main:app --reload
```

## Docker

Build the Docker image:

```bash
docker build -t vidy-ai .
```

Run the Docker container:

```bash
docker run --env-file .env -p 8000:8000 vidy-ai
```

To deploy the app in google cloud run, follow the steps below:

Open cloud console and run terminal commands

forward port 8000 to ngrok port

install ngrok

```bash
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc > /dev/null
```

```bash
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list > /dev/null
```

```bash
sudo apt update
```

```bash
sudo apt install ngrok
```

```bash
ngrok config add-authtoken 2nJAoSxt1ymAbqGG9706r18ixzQ_7Geu6tqtCJqwP8Tt4gpZC
```

```bash
ngrok tunnel --label edge=edghts_2nK4gxhqiUzrfKma4oJGxZwPcM2 http://localhost:8000
```

https://visually-powerful-cod.ngrok-free.app/

Now you’re ready to use TextBookAi!
