ARG BUILD_DIR=/build

# Build Container
FROM --platform=$BUILDPLATFORM node:20-alpine AS build

ARG BUILD_DIR

RUN mkdir ${BUILD_DIR}
WORKDIR ${BUILD_DIR}

COPY .htmlnanorc \
    package.json \
    package-lock.json \
    postcss.config.js \
    tailwind.config.js \
    vite.config.js \
    ./

RUN npm ci

COPY client ./client
RUN npm run build

# Runtime Container
FROM python:3.12-slim

ARG BUILD_DIR

ENV PUID=1000
ENV PGID=1000
ENV EXEC_TOOL=gosu
ENV FLATNOTES_HOST=0.0.0.0
ENV FLATNOTES_PORT=8080

ENV APP_PATH=/app
ENV FLATNOTES_PATH=/data

RUN mkdir -p ${APP_PATH}
RUN mkdir -p ${FLATNOTES_PATH}

RUN apt-get update -o Acquire::Retries=5 && apt-get install -y --no-install-recommends \
    curl \
    gosu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR ${APP_PATH}

COPY LICENSE ./
RUN pip install --no-cache-dir \
    whoosh==2.7.4 \
    fastapi==0.118.3 \
    "uvicorn[standard]==0.37.0" \
    aiofiles==25.1.0 \
    "python-jose[cryptography]==3.5.0" \
    pyotp==2.9.0 \
    qrcode==8.2 \
    python-multipart==0.0.20

COPY server ./server
COPY --from=build --chmod=777 ${BUILD_DIR}/client/dist ./client/dist

COPY entrypoint.sh healthcheck.sh /
RUN sed -i 's/\r$//' /entrypoint.sh /healthcheck.sh && \
    chmod +x /entrypoint.sh /healthcheck.sh

VOLUME /data
EXPOSE ${FLATNOTES_PORT}/tcp
HEALTHCHECK --interval=60s --timeout=10s CMD /healthcheck.sh

ENTRYPOINT [ "/entrypoint.sh" ]
