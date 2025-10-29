FROM python:3.9-slim

# Set working directory
WORKDIR /opt/proofpoint

# Install dependencies
RUN pip install --no-cache-dir websocket-client

# Copy the Python script and configuration file
COPY proofpoint.py  /opt/proofpoint/proofpoint_stream.py
COPY credentials.conf /opt/proofpoint/credentials.conf
COPY start.sh  /opt/proofpoint/start.sh
RUN chmod +x  /opt/proofpoint/start.sh
# Ensure the logs directory is created
RUN mkdir -p /opt/proofpoint/logs

# Set permissions for the configuration file
RUN chmod 600 /opt/proofpoint/credentials.conf

# Command to run the application
CMD ["python3", "proofpoint_stream.py"]

############################################
# docker build -t proofpoint-beat:p.v1  .  #
############################################
