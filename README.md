# Climate Hazard Trend Analyzer

A climate data analysis application that retrieves historical weather observations, identifies heatwave events, and analyzes their frequency and intensity over time.

> **Project status:** Backend implementation and automated validation are in progress. The backend includes historical weather ingestion, heatwave analysis, annual summaries, and linear trend calculations. Frontend integration and deployment will be added as they are completed.

## Overview

Climate hazards are easier to understand when historical observations are converted into measurable indicators. This project focuses on identifying heatwaves from daily maximum temperatures and analyzing how their occurrence changes over a selected period.

The application uses Python and FastAPI for its backend, MongoDB for historical weather storage and caching, and the Open-Meteo Historical Weather API as its data source.

The initial scope focuses on heatwaves rather than implementing multiple climate hazards incompletely.

## Features

### Backend

- REST API built with FastAPI.
- Historical weather ingestion from Open-Meteo.
- Asynchronous HTTP requests and MongoDB operations.
- MongoDB storage and caching for daily weather observations.
- Upsert-based ingestion to avoid duplicate logical records.
- Pydantic request and document validation.
- Geographic coordinate and date-range validation.
- Configurable environment settings.
- Centralized application error handling.
- Request IDs and request-duration logging.
- Health endpoint with database connectivity checks.
- Historical baseline calculation using the 95th percentile.
- Heatwave detection based on consecutive hot days.
- Annual heatwave frequency and duration summaries.
- Comparison between early and recent periods.
- Linear regression trend analysis of annual heatwave event counts.
- Trend direction, slope, and \(R^2\) reporting where defined.
- Compound unique index for daily weather records.
- Automated tests for trend calculations, heatwave analysis, and provider date-coverage validation.

### Planned improvements

- More efficient partial-range caching to fetch only missing date ranges.
- Expanded automated tests for cache integrity, API failures, and edge cases.
- React dashboard with interactive charts and summary insights.
- Production deployment and public application URL.

## Technology Stack

| Area | Technology |
|---|---|
| Backend framework | FastAPI |
| Language | Python |
| Data validation | Pydantic |
| Database | MongoDB |
| Database driver | PyMongo Async API |
| HTTP client | HTTPX |
| Numerical calculations | NumPy |
| Testing | Pytest |
| Containerized database | Docker Compose |
| Historical weather data | Open-Meteo Archive API |
| Frontend | React — planned |

## Architecture

```text
React Frontend (planned)
        |
        | HTTP / JSON
        v
FastAPI Application
        |
        +-- API Routes
        |     +-- Weather Ingestion
        |     +-- Heatwave Analysis
        |
        +-- Request Validation
        |
        +-- Services
        |     +-- Open-Meteo Integration
        |     +-- MongoDB Cache and Storage
        |     +-- Heatwave Detection
        |     +-- Annual Summaries
        |     +-- Trend Analysis
        |
        +-- Core Infrastructure
        |     +-- Configuration
        |     +-- Logging
        |     +-- Error Handling
        |
        +-----------> MongoDB
        |             Cached and stored observations
        |
        +-----------> Open-Meteo Archive API
                      External historical weather data
```

### Data flow

1. A client submits geographic coordinates and a date range.
2. FastAPI validates the request.
3. The weather service checks MongoDB for cached observations.
4. If the requested range is not fully covered by valid cached temperatures, the service retrieves historical data from Open-Meteo.
5. Daily observations are validated and stored in MongoDB using upserts.
6. The analysis service loads the historical baseline and requested observations.
7. The heatwave detection logic identifies qualifying events.
8. The API returns detected events, annual summaries, comparison metrics, and trend results as JSON.

## Data Source

**Open-Meteo Historical Weather API**

Endpoint: https://archive-api.open-meteo.com/v1/archive

The initial implementation uses the daily `temperature_2m_max` variable, measured in degrees Celsius, with the ERA5 model selected in the request.

The application stores the provider, model, coordinates, observation date, and maximum temperature alongside each record.

Source documentation: https://open-meteo.com/en/docs/historical-weather-api

## Heatwave Detection Methodology

### 1. Historical baseline

The current implementation uses January 1, 1991, through December 31, 2020, as the reference baseline.

The 95th percentile of valid daily maximum temperatures in this period is calculated for the requested coordinates.

### 2. Event definition

A heatwave is defined as at least three consecutive calendar days with daily maximum temperatures strictly above the calculated threshold.

For example, if the threshold is 35°C:

- Day 1: 36°C
- Day 2: 37°C
- Day 3: 35.5°C

These three consecutive days qualify as a heatwave.

A sequence of only two qualifying days does not qualify. A missing observation or a non-hot day breaks the consecutive-day sequence.

### 3. Event metrics

For every detected event, the backend calculates:

- Start date and end date.
- Duration in days.
- Peak temperature.
- Mean temperature during the event.
- Mean temperature excess above the threshold.

### 4. Annual summaries

The analysis service groups events by their starting year and calculates:

- Number of heatwave events.
- Total heatwave days.
- Average event duration.
- Average temperature excess above the threshold.

### 5. Period comparison

A linear regression is also calculated over annual heatwave event counts to estimate the direction and slope of change. The result includes the estimated slope in events per year, trend direction, \(R^2\) where defined, and the number of years analyzed. This descriptive trend does not establish causation or statistical significance.

## API

The following endpoints are intended to document the current backend routes. Verify their exact paths against the registered FastAPI routers before submission.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Application information |
| GET | `/health` | Application and database health check |
| POST | `/api/weather/ingest` | Retrieve and cache historical daily weather |
| POST | `/api/analysis/heatwaves` | Analyze heatwaves for a location and period |

### Weather ingestion example

Request:

```json
{
  "latitude": 17.385,
  "longitude": 78.4867,
  "start_date": "2015-01-01",
  "end_date": "2015-12-31"
}
```

Example request using curl:

```bash
curl.exe -X POST "http://127.0.0.1:8000/api/weather/ingest" `
  -H "Content-Type: application/json" `
  -d '{"latitude":17.385,"longitude":78.4867,"start_date":"2015-01-01","end_date":"2015-12-31"}'
```

The response uses a consistent structure:

```json
{
  "success": true,
  "message": "Historical weather data retrieved successfully",
  "data": {
    "source": "open-meteo",
    "records": 365,
    "latitude": 17.385,
    "longitude": 78.4867,
    "start_date": "2015-01-01",
    "end_date": "2015-12-31"
  },
  "meta": {}
}
```

The record count and cache source can vary depending on the requested dates and data already stored.

Interactive API documentation is available at `/docs` when the application is running.

## MongoDB Data Model

Daily weather observations are stored in the `daily_weather` collection.

A record contains:

| Field | Description |
|---|---|
| `latitude` | Rounded latitude |
| `longitude` | Rounded longitude |
| `date` | Observation date in ISO format |
| `temperature_max_c` | Daily maximum temperature, or `null` when unavailable |
| `source` | Data provider identifier |
| `model` | Weather model identifier |

A unique compound index uses the following fields:

`latitude + longitude + date + source + model`

This enforces the logical identity of a daily observation and supports location/date-based lookups.

## Local Setup

### Prerequisites

- Python 3.11 or later, compatible with the installed dependencies.
- Docker Desktop with Docker Compose.
- Git.

### 1. Clone the repository

```bash
git clone <YOUR_BACKEND_REPOSITORY_URL>
cd climate-hazard-analyzer-backend
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script activation, use the appropriate local execution-policy setting or activate the environment through another supported terminal.

### 3. Install dependencies

If a `requirements.txt` file is present:

```powershell
python -m pip install -r requirements.txt
```

Otherwise, install the packages used by the current implementation:

```powershell
python -m pip install "fastapi[standard]" pymongo pydantic-settings httpx numpy pytest
```

Once the dependency list is finalized, commit a reproducible dependency file.

### 4. Configure environment variables

Create a `.env` file in the backend root:

```dotenv
APP_NAME="Climate Hazard Trend Analyzer"
APP_ENV=development

MONGO_ROOT_USERNAME=climate_admin
MONGO_ROOT_PASSWORD=replace_with_a_strong_local_password

MONGODB_URL=mongodb://climate_admin:URL_ENCODED_PASSWORD@localhost:27018/climate_hazard_db?authSource=admin
MONGODB_DATABASE=climate_hazard_db

CORS_ORIGINS=http://localhost:5173
```

Replace the example password with your own. URL-encode reserved characters in the MongoDB URI password; for example, `@` becomes `%40`.

Do not commit `.env` or real credentials to Git.

### 5. Start MongoDB

The project uses Docker Compose for the local database.

```powershell
docker compose up -d
```

Check that the container is running:

```powershell
docker compose ps
```

The local MongoDB port is `27018` on the host, mapped to `27017` inside the container.

### 6. Start the backend

Run from the backend root:

```powershell
python -m uvicorn app.main:app --reload
```

Open:

- Application: http://127.0.0.1:8000
- Health check: http://127.0.0.1:8000/health
- Swagger UI: http://127.0.0.1:8000/docs

## Testing

Run the automated tests from the backend root:

```powershell
python -m pytest -v
```

The current test suite includes coverage for:

- Linear trend calculations for increasing, decreasing, constant, and insufficient-data cases.
- Heatwave analysis integration with mocked dependencies.
- Provider date-coverage validation, including missing and duplicate dates.

Further testing will cover:

- Heatwave detection at the minimum duration boundary.
- Events interrupted by non-hot days or missing observations.
- Percentile calculations and invalid input.
- Weather document validation.
- Cache behavior for complete and incomplete date ranges.
- API validation, provider failures, and error responses.

Test coverage will be expanded as the implementation progresses.

## Assumptions and Limitations

- The analysis initially focuses on heatwaves only.
- The reference baseline is fixed to 1991–2020.
- The threshold is calculated across all valid daily maximum temperatures in the baseline, rather than using a separate percentile for each calendar day.
- The heatwave threshold comparison is strictly greater than the percentile threshold.
- Events are grouped into annual summaries by their start year.
- The current early-versus-recent comparison is a descriptive comparison, not proof of a long-term climate trend or causation.
- Missing observations must not be treated as non-hot days without explicitly acknowledging the resulting uncertainty.
- Historical API coverage and data quality can vary by location and date.
- The current implementation does not yet cover every climate hazard or all production safeguards.

## Security and Performance Considerations

The current implementation includes request validation, environment-based configuration, centralized error handling, request logging, database connectivity checks, MongoDB caching, and a unique compound index.

Further work before production deployment includes:

- Efficient partial-range cache retrieval.
- Request throttling or rate limiting.
- Strict production CORS configuration.
- Continued validation of provider failures and malformed responses.
- Expanded automated tests for edge cases.
- Production secrets management.
- Monitoring, deployment health checks, and resource limits.

The local Docker database is not automatically accessible to a deployed backend. A deployment must use a remotely reachable MongoDB service or a deliberately configured private network.

## Deployment

Deployment URLs will be added after the services are deployed and verified.

- **Backend API:** `<BACKEND_DEPLOYMENT_URL>`
- **Frontend application:** `<FRONTEND_DEPLOYMENT_URL>`
- **API documentation:** `<BACKEND_DEPLOYMENT_URL>/docs`

The frontend and backend are maintained separately. The deployed backend must use a remote database connection, and its CORS configuration must allow the actual frontend origin.

## Future Improvements

- React dashboard with interactive annual trend charts.
- Region selection through a map or coordinate inputs.
- Rolling-average visualizations.
- Exportable CSV or PDF reports.
- Better treatment of incomplete historical observations.
- More efficient partial-range caching.
- Additional hazard definitions for droughts and heavy rainfall.
- More comprehensive automated tests and production monitoring.

## AI Tool Disclosure

ChatGPT was used as a development assistant to help reason about backend architecture, understand implementation choices, review code, troubleshoot errors, and plan validation and testing.

The implementation is being reviewed and tested incrementally, with attention to understanding the design decisions and being able to explain and modify the code during a technical walkthrough.

All tools used during development should be disclosed accurately in the final submission.

## Author

**Developer:** `<YOUR_NAME>`

**Repository:** `<YOUR_BACKEND_REPOSITORY_URL>`

**Application:** `<FRONTEND_DEPLOYMENT_URL>`
