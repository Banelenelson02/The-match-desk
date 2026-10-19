FROM python:3.12-slim
WORKDIR /app
COPY matchdesk ./matchdesk
COPY web ./web
RUN useradd --create-home appuser
USER appuser
ENV HOST=0.0.0.0 PORT=8000
EXPOSE 8000
CMD ["python", "-m", "matchdesk.server"]
