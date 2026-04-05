FROM alpine:3.19

# Install bash for better scripting (lightweight)
RUN apk add --no-cache bash

# Create test runner script
COPY run_test.sh /usr/local/bin/run_test.sh
RUN chmod +x /usr/local/bin/run_test.sh

# Default command runs the test imitation
CMD ["/usr/local/bin/run_test.sh"]