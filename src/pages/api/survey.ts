import type { APIRoute } from 'astro';
import { insertResponse } from '../../lib/survey-db';

export const POST: APIRoute = async ({ request }) => {
    let answers: Record<string, string>;

    try {
        answers = await request.json();
    } catch {
        return new Response('Invalid JSON.', { status: 400 });
    }

    // Browser validation improves usability, but the API must independently
    // reject incomplete payloads because API requests can bypass the page.
    if (
        typeof answers.age !== 'string' ||
        typeof answers.gender !== 'string' ||
        typeof answers.education !== 'string'
    ) {
        return new Response('Demographic answers are required.', { status: 400 });
    }

    for (let question = 1; question <= 28; question += 1) {
        if (typeof answers[`Question ${question}`] !== 'string') {
            return new Response(`Question ${question} is required.`, { status: 400 });
        }
    }

    for (let question = 1; question <= 6; question += 1) {
        if (typeof answers[`GenAI Question ${question}`] !== 'string') {
            return new Response(`GenAI Question ${question} is required.`, { status: 400 });
        }
    }

    for (let question = 1; question <= 8; question += 1) {
        if (typeof answers[`Self-Efficacy Question ${question}`] !== 'string') {
            return new Response(`Self-Efficacy Question ${question} is required.`, { status: 400 });
        }
    }

    insertResponse.run(
        answers.age,
        answers.gender,
        answers.education,
        answers['Self-Efficacy Question 1'],
        answers['Self-Efficacy Question 2'],
        answers['Self-Efficacy Question 3'],
        answers['Self-Efficacy Question 4'],
        answers['Self-Efficacy Question 5'],
        answers['Self-Efficacy Question 6'],
        answers['Self-Efficacy Question 7'],
        answers['Self-Efficacy Question 8'],
        JSON.stringify(answers)
    );

    return new Response(null, { status: 201 });
};
