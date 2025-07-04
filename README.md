# WebViewer-V2-BackEnd



python manage.py runserver 8000


# WebViewer V2 Backend

A GIS-focused REST API built with **Django**, **Django REST Framework**, and **GeoDjango**. It powers a Web GIS application for managing projects, layers, styles, basemaps, and more.

---

## ✨ Features

### 🔑 Users & Authentication

- Custom User model with JWT authentication (via `token_obtain_pair`)
- Audit logging for create/update/delete actions

### 🏢 Clients

- Manage client organizations and access control
- `ClientProject` links clients to projects with unique share links

### 🌍 Projects

- Map configurations: center, zoom, basemaps, tools
- Support for public/private visibility

### 📂 Layers

- Supports multiple layer groups, types, and uploads
- CRS transformation and bulk feature loading (in `layers/file_utils.py`)
- `ProjectLayerData` stores geometries and properties

### 🎨 Styling

- Marker libraries, popup templates, categorized styles
- Color palettes and reusable style definitions

### 🌐 Basemaps

- Supports OSM, Google, Bing, and custom tile servers
- Preview via `preview` action in `BasemapViewSet`

### ⚙️ Functions & Tools

- Executable layer functions (e.g., clustering)
- Configurable project tools

---

## 📁 Project Structure

```
WebViewer-V2-BackEnd/
├── WebViewerV2/        # Global settings and URLs
├── basemaps/           # Basemap API and models
├── clients/            # Organizations and sharing logic
├── functions/          # Map tools and layer functions
├── layers/             # GIS data models and import logic
├── projects/           # Project configs and cloning
├── styling/            # Styles, markers, templates
├── users/              # Auth and audit logs
├── tests/              # Integration test suite
├── schema.yaml         # OpenAPI definition
├── Dockerfile          # GDAL/GEOS container setup
└── requirements.txt    # Python dependencies
```

Each Django app contains `models.py`, `serializers.py`, `views.py`, `urls.py`, and `tests.py`.

---

## 🔧 Configuration

Environment variables (see `WebViewerV2/settings.py`):

```env
SECRET_KEY=...
DEBUG=True
DATABASE_NAME=...
DATABASE_USER=...
DATABASE_PASSWORD=...
DATABASE_HOST=...
DATABASE_PORT=...
JWT_SECRET_KEY=...
CORS_ALLOWED_ORIGINS=http://localhost:3000
AZURE_STORAGE_ACCOUNT_NAME=...
AZURE_STORAGE_ACCOUNT_KEY=...
AZURE_STORAGE_CONTAINER_NAME=...
FRONTEND_BASE_URL=https://example.com
```

Upload directory: `media/temp_uploads` (created on startup)

---

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/Nard248/WebViewer-V2-BackEnd.git
cd WebViewer-V2-BackEnd
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

> Ensure GDAL and GEOS are installed (see Dockerfile for reference)

### 3. Configure environment

Create a `.env` file and fill in the variables listed above.

### 4. Run the server

```bash
python manage.py runserver
```
---

## 🛂 Docker Support

```bash
docker build -t webviewer-v2 .
docker run -p 8000:8000 --env-file .env webviewer-v2
```

> Includes GDAL/GEOS installation and launches Django dev server.

---

## 📄 API Documentation

- Swagger UI: [`/api/docs/`](http://localhost:8000/api/docs/)
- Redoc: [`/api/redoc/`](http://localhost:8000/api/redoc/)

---

## 🔮 Tests

Run the full test suite:

```bash
pytest
```

> Configured via `pytest.ini`. Integration tests in `tests/test_integration.py` include user/client/project setup & permissions validation.

---

## 🔍 Explore More

- Check `manual_utils/uploading_pipeline.py` for scripted data uploads.
- Review the `api/docs` file to explore all endpoints.
- Dive into apps under `clients/`, `projects/`, `layers/`, etc., for customization.

---

