FROM python:3.13-slim

# Install build tools & Rust (needed for some dependencies)
RUN apt-get update && apt-get install -y curl build-essential
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .
# Change the entrypoint below if your main Flask app is not in main.py
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:8000"]
