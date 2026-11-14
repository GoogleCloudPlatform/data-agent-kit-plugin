# Dataflow Flex Template - Single Docker Image Configuration

This document provides reference guidelines for building and launching
Dataflow Flex templates using the **Single Docker Image** configuration.

---

## 1. Dockerfile Guidelines

Use this template to build custom container images where workers run
the **exact same image** that launched the job.

### Template

```dockerfile
ARG IMAGE_PYTHON_VERSION=3.11

# --- Stage 1: Get Python Flex Template Launcher Binary ---
FROM gcr.io/dataflow-templates-base/python3-template-launcher-base:latest AS launcher

# --- Stage 2: Build Application Image ---

# Always look up and use the latest Apache Beam SDK version unless user instructed to use a specific version.
FROM apache/beam_python${IMAGE_PYTHON_VERSION}_sdk:<LATEST_VERSION>

# 1. Copy Flex Template launcher binary (Path is STRICT)
COPY --from=launcher /opt/google/dataflow/python_template_launcher /opt/google/dataflow/python_template_launcher

# 2. Set working directory
WORKDIR /template

# 3. Install Python Dependencies
COPY requirements.txt setup.py ./
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy custom source FIRST
COPY src/ src/

# 5. Install Workspace Package
RUN pip install --no-cache-dir -e .

# 6. Specify Pipeline Entrypoint
ENV FLEX_TEMPLATE_PYTHON_PY_FILE=/template/<PATH_TO_PIPELINE_LAUNCHER_FILE>
```

> [!IMPORTANT]
> **CRITICAL RULES:**
> - Do NOT override ENTRYPOINT (Workers need /opt/apache/beam/boot).
> - Do NOT set FLEX_TEMPLATE_PYTHON_REQUIREMENTS_FILE or
>   FLEX_TEMPLATE_PYTHON_SETUP_FILE
>   (These dependencies are already installed in the image).
---

## 2. Launch Guidance

*   **Explicitly Pass Custom Worker Image**:
    *   If you build a custom image for your Flex Template,
        you **must supply it at runtime** when launching the template.
    *   **Example (using `gcloud`)**: Pass it as a parameter string: `--parameters sdk_container_image="[IMAGE_URI]"`