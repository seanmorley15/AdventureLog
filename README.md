# AdventureLog: Embark, Explore, Remember. 🌍

_**⚠️ AdventureLog is in early development and is not recommended for production use until version 1.0!**_

### _"Never forget an adventure with AdventureLog - Your ultimate travel companion!"_

---

## Installation

### Docker 🐋 (Recomended)

1. Clone the repository
2. Edit the `docker-compose.yml` file and change the database password
3. Run `docker compose up -d` to build the image and start the container
4. Wait for the app to start up and migrate then visit the port and enjoy!
5. After navigating to the app, fill out the form to create the admin user.

**Note**: The `ORIGIN` variable is required for CSRF protection. It can be omitted if using a reverse proxy or other HTTPS service.

## About AdventureLog ℹ️

AdventureLog is a Svelte Kit application that utilizes a PostgreSQL database. Users can log the adventures they have experienced, as well as plan future ones. Key features include:

- Logging past adventures with fields like name, date, location, description, and rating.
- Planning future adventures with similar fields.
- Tagging different activity types for better organization.
- Viewing countries, regions, and marking visited regions.

AdventureLog aims to be your ultimate travel companion, helping you document your adventures and plan new ones effortlessly.

AdventureLog is liscensed under the GNU General Public License v3.0.

## Roadmap 🛣️

- Improved mobile device support
- Password reset functionality
- Improved error handling
- Handling of adventure cards with variable width
