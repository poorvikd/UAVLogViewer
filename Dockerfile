FROM --platform=$BUILDPLATFORM node:20

# Add build arguments for platform
ARG TARGETPLATFORM
ARG BUILDPLATFORM
ARG TARGETARCH

# Create app directory
WORKDIR /usr/src/app

# Install git and other dependencies
RUN apt-get update && apt-get install -y \
  git \
  python3 \
  make \
  g++ \
  && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m -u 2000 nodeuser

# Copy package files first for better caching
COPY package*.json ./

# Install dependencies with platform-specific optimizations
RUN npm install --target_arch=$TARGETARCH

# Bundle app source
COPY . .

# Initialize and update git submodules
RUN git init && \
  git submodule init && \
  git submodule update

# Run the update-browserslist-db as suggested in the warning
RUN npx update-browserslist-db@latest

# Change ownership of the app directory to the non-root user
RUN chown -R nodeuser:nodeuser /usr/src/app

# Switch to non-root user
USER nodeuser

# Configure git to trust the mounted directory
RUN git config --global --add safe.directory /usr/src/app

EXPOSE 8080
CMD [ "npm", "run", "dev" ]
