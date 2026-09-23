import { fileURLToPath } from 'node:url';

// The Standard Deployment image creates this superuser on first boot.
export const ADMIN = { username: 'admin', password: 'admin' };

// Written by auth.setup.ts and loaded by every spec in the chromium project.
export const ADMIN_STORAGE_STATE = fileURLToPath(new URL('./.auth/admin.json', import.meta.url));
