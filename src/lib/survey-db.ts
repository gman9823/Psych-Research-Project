import { mkdirSync } from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import { dirname, resolve } from 'node:path';

// Keep the database beside the application so local and deployed runs use a
// predictable location separate from version-controlled source.
const databasePath = resolve(process.cwd(), 'data', 'survey.sqlite');
mkdirSync(dirname(databasePath), { recursive: true });

export const database = new DatabaseSync(databasePath);

// Store demographics in dedicated columns while keeping the complete
// questionnaire payload for future analysis and schema changes.
database.exec(`
    CREATE TABLE IF NOT EXISTS survey_responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        age TEXT NOT NULL,
        gender TEXT NOT NULL,
        education TEXT NOT NULL,
        answers TEXT NOT NULL
    )
`);

const responseColumns = database.prepare('PRAGMA table_info(survey_responses)').all() as Array<{ name: string }>;
const columnNames = new Set(responseColumns.map((column) => column.name));

// Existing databases may not yet have the self-efficacy columns, so migrate
// them in place without replacing or deleting stored responses.
for (let question = 1; question <= 8; question += 1) {
    const columnName = `self_efficacy_${question}`;
    if (!columnNames.has(columnName)) {
        database.exec(`ALTER TABLE survey_responses ADD COLUMN ${columnName} TEXT`);
    }
}

export const insertResponse = database.prepare(`
    INSERT INTO survey_responses (
        age,
        gender,
        education,
        self_efficacy_1,
        self_efficacy_2,
        self_efficacy_3,
        self_efficacy_4,
        self_efficacy_5,
        self_efficacy_6,
        self_efficacy_7,
        self_efficacy_8,
        answers
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
`);
