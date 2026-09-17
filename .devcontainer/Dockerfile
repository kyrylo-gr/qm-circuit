FROM mcr.microsoft.com/devcontainers/python:3.12

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    acl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /workspace

USER vscode
RUN curl -fsSL https://claude.ai/install.sh | bash
RUN claude plugins install mattpocock-skills
RUN claude plugins marketplace add DietrichGebert/ponytail
RUN claude plugin install ponytail@ponytail
RUN npx skills add JuliusBrussee/caveman -g