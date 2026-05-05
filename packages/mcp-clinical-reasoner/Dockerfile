FROM python:3.12-slim

# Stub image — mcp-clinical-reasoner not yet implemented (Phase 3.4)
RUN echo '#!/bin/sh\necho "mcp-clinical-reasoner: coming in Phase 3.4 (weeks 6-7)"\nexit 1' \
    > /usr/local/bin/mcp-clinical-reasoner && chmod +x /usr/local/bin/mcp-clinical-reasoner

ENTRYPOINT ["mcp-clinical-reasoner"]
