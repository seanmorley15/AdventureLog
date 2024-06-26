# Use this image as the platform to build the app
FROM node:18-alpine AS external-website

# A small line inside the image to show who made it
LABEL Developers="Sean Morley"

# The WORKDIR instruction sets the working directory for everything that will happen next
WORKDIR /app

# Copy all local files into the image
COPY . .

# Install pnpm
RUN npm install -g pnpm

# Clean install all node modules using pnpm
RUN pnpm install

# Build SvelteKit app
RUN npm run build

# Expose the port that the app is listening on
EXPOSE 3000

RUN chmod +x ./startup.sh

# The USER instruction sets the user name to use as the default user for the remainder of the current stage
USER node:node

# Run startup.sh instead of the default command
CMD ["./startup.sh"]