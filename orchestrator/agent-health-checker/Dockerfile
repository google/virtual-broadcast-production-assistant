# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the requirements file into the container at /usr/src/app
COPY requirements-prod.txt ./

# Install any needed packages specified in requirements-prod.txt
RUN pip install --no-cache-dir -r requirements-prod.txt

# Copy the rest of the application's code from the host to the container at /usr/src/app
COPY . .

# Define the command to run on container startup
CMD [ "python", "./main.py" ]
