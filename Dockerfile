FROM python:3.11

# Install GeoDjango dependencies with specific GDAL version
RUN apt-get update && apt-get install -y \
    binutils \
    libproj-dev \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    && rm -rf /var/lib/apt/lists/*

# Find and set the correct GDAL library paths
RUN ldconfig && \
    # Find actual GDAL library path
    GDAL_PATH=$(find /usr/lib -name "libgdal.so.*" | head -n 1) && \
    # Create a symlink if the file is found but not at the expected path
    if [ -n "$GDAL_PATH" ] && [ ! -f "/usr/lib/libgdal.so" ]; then \
        ln -s $GDAL_PATH /usr/lib/libgdal.so; \
    fi && \
    # Find actual GEOS library path
    GEOS_PATH=$(find /usr/lib -name "libgeos_c.so.*" | head -n 1) && \
    # Create a symlink if the file is found but not at the expected path
    if [ -n "$GEOS_PATH" ] && [ ! -f "/usr/lib/libgeos_c.so" ]; then \
        ln -s $GEOS_PATH /usr/lib/libgeos_c.so; \
    fi && \
    # Print library locations for debugging
    echo "GDAL at: $(find /usr/lib -name 'libgdal.so*')" && \
    echo "GEOS at: $(find /usr/lib -name 'libgeos_c.so*')"

# Set GDAL environment variables to the actual location
ENV GDAL_LIBRARY_PATH=/usr/lib/libgdal.so
ENV GEOS_LIBRARY_PATH=/usr/lib/libgeos_c.so

# Set environment variables for Django
ENV RUNNING_IN_DOCKER=True
ENV DATABASE_NAME=web_viewer
ENV DATABASE_USER=postgresqlwireless2020
ENV DATABASE_PASSWORD=software2020!!
ENV DATABASE_HOST=wirelesspostgresqlflexible.postgres.database.azure.com
ENV DATABASE_PORT=5432
ENV DATABASE_SCHEMA=web_viewer

# Set up your application
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Set development server command
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]