# Start with a lightweight Python image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the Docker image
COPY requirements.txt /app/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

# Copy the entire application into the container
COPY . /app

# Expose the correct port for Cloud Run
EXPOSE 8080

# Set the environment variable for Cloud Run's required port
ENV PORT=8080

# Run Gunicorn with proper port binding
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "run:app"]
