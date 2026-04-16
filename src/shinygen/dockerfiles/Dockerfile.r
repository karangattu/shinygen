# Combined R + Python sandbox for Shiny R app generation.
# Base: rocker/r-ver provides R 4.4; Python 3.12 added on top.

FROM rocker/r-ver:4.4.2

# System deps for R packages, Python, and Chromium (Playwright)
# Includes build tooling (cmake, pkg-config) required by recent CRAN packages
# such as `fs` (libuv) and geospatial stack deps (gdal, udunits, proj, geos)
# required by leaflet -> sf -> s2/units/terra.
# and gh CLI (used by codex for GitHub OAuth — avoids OPENAI_API_KEY)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    pkg-config \
    git \
    python3 \
    python3-pip \
    python3-venv \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    libfontconfig1-dev \
    libfreetype6-dev \
    libpng-dev \
    libtiff5-dev \
    libjpeg-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    libudunits2-dev \
    libsqlite3-dev \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libpango-1.0-0 libcairo2 \
    libasound2t64 libnspr4 libdbus-1-3 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && gh extension install github/copilot-cli --force \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Pre-install R packages
RUN Rscript -e ' \
    install.packages(c( \
        "shiny", "bslib", "bsicons", \
        "ggplot2", "dplyr", "readr", "tidyr", "stringr", "lubridate", \
        "plotly", "DT", "leaflet", \
        "scales", "thematic", "htmltools", "htmlwidgets" \
    ), repos = "https://cloud.r-project.org") \
'

# Python packages
RUN pip3 install --break-system-packages --no-cache-dir \
    shiny \
    plotly \
    faicons \
    pandas \
    matplotlib \
    seaborn \
    great-tables \
    itables \
    htmltools \
    shinywidgets \
    playwright \
    github-copilot-sdk

# Install Chromium for Playwright (used by agent for visual self-evaluation)
RUN playwright install chromium

# Working directory
RUN mkdir -p /home/user/project
WORKDIR /home/user/project

CMD ["sleep", "infinity"]
