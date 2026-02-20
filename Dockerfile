# Stage 1: build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: run Python backend + serve built frontend
FROM python:3.12-slim
WORKDIR /app

# Copy backend
COPY backend/ ./backend/

# Copy built frontend from stage 1
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Install Python deps
RUN pip install --no-cache-dir -r backend/requirements.txt

# Render and most hosts set PORT
ENV PORT=8000
ENV NODE_ENV=production
EXPOSE 8000

# Run from repo root so backend can find frontend/dist at ./frontend/dist
WORKDIR /app
CMD ["python", "backend/run_server.py"]
