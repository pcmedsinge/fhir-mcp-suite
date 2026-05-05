FROM python:3.12-slim

# Stub image — mcp-terminology not yet implemented (Phase 3.3)
RUN echo '#!/bin/sh\necho "mcp-terminology: coming in Phase 3.3 (weeks 4-5)"\nexit 1' \
    > /usr/local/bin/mcp-terminology && chmod +x /usr/local/bin/mcp-terminology

ENTRYPOINT ["mcp-terminology"]
