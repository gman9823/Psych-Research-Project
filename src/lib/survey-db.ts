import { mkdirSync } from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import { dirname, resolve } from 'node:path';
import { createClient } from '@libsql/client';

const tursoUrl = import.meta.env.TURSO_DATABASE_URL
    || process.env.TURSO_DATABASE_URL;
const tursoToken = import.meta.env.TURSO_AUTH_TOKEN
    || import.meta.env.TURSO_DATABASE_TOKEN
    || process.env.TURSO_AUTH_TOKEN
    || process.env.TURSO_DATABASE_TOKEN;

export const db = tursoUrl
    ? createClient({ url: tursoUrl, authToken: tursoToken })
    : null;

let localInsert: ReturnType<DatabaseSync['prepare']> | null = null;

if (!db) {
    // Local development retains a durable SQLite file when Turso credentials
    // are absent; deployed Turso runs never write to ephemeral Render storage.
    const databasePath = resolve(process.cwd(), 'data', 'survey.sqlite');
    mkdirSync(dirname(databasePath), { recursive: true });
    const localDatabase = new DatabaseSync(databasePath);
    localDatabase.exec(`
        CREATE TABLE IF NOT EXISTS survey_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            age TEXT NOT NULL,
            gender TEXT NOT NULL,
            education TEXT NOT NULL,
            self_efficacy_1 TEXT,
            self_efficacy_2 TEXT,
            self_efficacy_3 TEXT,
            self_efficacy_4 TEXT,
            self_efficacy_5 TEXT,
            self_efficacy_6 TEXT,
            self_efficacy_7 TEXT,
            self_efficacy_8 TEXT,
            answers TEXT NOT NULL
        )
    `);
    localInsert = localDatabase.prepare(`
        INSERT INTO survey_responses (
            age, gender, education,
            self_efficacy_1, self_efficacy_2, self_efficacy_3, self_efficacy_4,
            self_efficacy_5, self_efficacy_6, self_efficacy_7, self_efficacy_8,
            answers
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);
}

let initializedRemote = false;

async function initializeRemote() {
    if (!db || initializedRemote) return;
    await db.executeMultiple(`
        CREATE TABLE IF NOT EXISTS survey_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            age TEXT NOT NULL,
            gender TEXT NOT NULL,
            education TEXT NOT NULL,
            self_efficacy_1 TEXT,
            self_efficacy_2 TEXT,
            self_efficacy_3 TEXT,
            self_efficacy_4 TEXT,
            self_efficacy_5 TEXT,
            self_efficacy_6 TEXT,
            self_efficacy_7 TEXT,
            self_efficacy_8 TEXT,
            answers TEXT NOT NULL
        );
    `);
    initializedRemote = true;
}

export async function insertResponse(values: string[]) {
    if (db) {
        await initializeRemote();
        await db.execute({
            sql: `
                INSERT INTO survey_responses (
                    age, gender, education,
                    self_efficacy_1, self_efficacy_2, self_efficacy_3, self_efficacy_4,
                    self_efficacy_5, self_efficacy_6, self_efficacy_7, self_efficacy_8,
                    answers
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            `,
            args: values
        });
        return;
    }
    localInsert?.run(...values);
}
